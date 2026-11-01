#!/usr/bin/env bash
# Compila el motor FTEQW (Quake) para Android y arma un APK firmado.
# Pensado para correr en GitHub Actions (ubuntu-latest, trae Android SDK + NDK).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${WORK:-$ROOT/build/quake}"
OUT="${OUT:-$ROOT/build/apk}"
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:?falta ANDROID_HOME}}"
NDK="${ANDROID_NDK_LATEST_HOME:-${ANDROID_NDK_HOME:?falta el NDK}}"
ABI="${ABI:-arm64-v8a}"

mkdir -p "$WORK" "$OUT"
cd "$WORK"

echo "== Motor FTEQW"
[ -d fteqw ] || git clone --depth 1 https://github.com/fte-team/fteqw fteqw

echo "== Parches al CMake del motor (OpenGL ES y sonido OpenSL en Android)"
# FIND_PACKAGE(OpenGL) no encuentra nada en el NDK; en Android siempre hay GLES.
sed -i 's/^FIND_PACKAGE(OpenGL)/IF(ANDROID)\nSET(OpenGL_FOUND TRUE)\nELSE()\nFIND_PACKAGE(OpenGL)\nENDIF()/' fteqw/CMakeLists.txt
grep -c "OpenGL_FOUND TRUE" fteqw/CMakeLists.txt
# Igual que el Makefile del motor: sonido con OpenSL ES.
sed -i 's|engine/client/snd_droid.c|engine/client/snd_opensl.c|' fteqw/CMakeLists.txt
sed -i 's|SET(FTE_LIBS ${FTE_LIBS} android log EGL ${SYS_LIBS}|SET(FTE_LIBS ${FTE_LIBS} android log EGL OpenSLES ${SYS_LIBS}|' fteqw/CMakeLists.txt
grep -n "OpenGL_FOUND TRUE\|snd_opensl\|OpenSLES" fteqw/CMakeLists.txt
# La biblioteca de Android no incluía el servidor (necesario para correr el QuakeC / un solo jugador).
sed -i '/ADD_LIBRARY(ftedroid MODULE/,/)/ s|\${FTE_CLIENT_FILES}|${FTE_CLIENT_FILES}\n\t\t\t${FTE_SERVER_FILES}|' fteqw/CMakeLists.txt
grep -n -A6 "ADD_LIBRARY(ftedroid" fteqw/CMakeLists.txt
# La llamada a VK_Init de Android quedó vieja: le falta el número de extensiones (1).
sed -i 's/VK_Init(info, extnames, VKVID_CreateSurface, NULL)/VK_Init(info, extnames, 1, VKVID_CreateSurface, NULL)/' fteqw/engine/gl/gl_viddroid.c
grep -n "VK_Init" fteqw/engine/gl/gl_viddroid.c

echo "== Herramientas Android"
PLATFORM="$(ls "$SDK/platforms" | grep -E '^android-[0-9]+$' | sort -t- -k2 -n | tail -1)"
BT="$(ls "$SDK/build-tools" | sort -V | tail -1)"
ANDROID_JAR="$SDK/platforms/$PLATFORM/android.jar"
BTOOLS="$SDK/build-tools/$BT"
echo "plataforma=$PLATFORM build-tools=$BT ndk=$NDK"

echo "== Compilando libftedroid.so ($ABI)"
cmake -S fteqw -B "build-$ABI" -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="$NDK/build/cmake/android.toolchain.cmake" \
  -DANDROID_ABI="$ABI" -DANDROID_PLATFORM=android-24 \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS="-fcommon"
cmake --build "build-$ABI" --target ftedroid -j"$(nproc)"
SO="$(find "build-$ABI" -name libftedroid.so | head -1)"
[ -n "$SO" ] || { echo "No se generó libftedroid.so"; exit 1; }

echo "== Java -> dex"
DROID="$WORK/fteqw/engine/droid"
rm -rf classes dex && mkdir -p classes dex
javac --release 8 -nowarn -cp "$ANDROID_JAR" -d classes $(find "$DROID/src" -name '*.java')
"$BTOOLS/d8" --release --min-api 24 --lib "$ANDROID_JAR" --output dex $(find classes -name '*.class')

echo "== Recursos y manifest"
rm -rf res.zip base.apk
"$BTOOLS/aapt2" compile --dir "$DROID/res" -o res.zip
"$BTOOLS/aapt2" link -o base.apk -I "$ANDROID_JAR" \
  --manifest "$DROID/AndroidManifest.xml" \
  --min-sdk-version 24 --target-sdk-version 28 \
  --version-code 1 --version-name 1.0 \
  res.zip

echo "== Armando el APK"
rm -rf stage && mkdir -p "stage/lib/$ABI"
cp dex/classes.dex stage/
cp "$SO" "stage/lib/$ABI/libftedroid.so"
cp "$DROID/fte.cfg" "$DROID/configs/touch.cfg" stage/
# manifiesto del juego (y datos propios) si existen
[ -f "$ROOT/quake/default.fmf" ] && cp "$ROOT/quake/default.fmf" stage/ || cp "$DROID/default.fmf" stage/
( cd stage && zip -q -r -0 ../base.apk . )

"$BTOOLS/zipalign" -p -f 4 base.apk aligned.apk
[ -f debug.keystore ] || keytool -genkeypair -keystore debug.keystore -storepass android -keypass android \
  -alias zombies -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Zombies Debug"
"$BTOOLS/apksigner" sign --ks debug.keystore --ks-pass pass:android --key-pass pass:android \
  --out "$OUT/zombies.apk" aligned.apk
"$BTOOLS/apksigner" verify "$OUT/zombies.apk"
ls -la "$OUT/zombies.apk"
echo "== Contenido del APK"
unzip -l "$OUT/zombies.apk"
"$BTOOLS/aapt2" dump badging "$OUT/zombies.apk" | head -20
