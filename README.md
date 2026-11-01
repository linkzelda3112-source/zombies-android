# Zombies Android (Unity)

Modo Zombies por rondas para Android: movimiento táctil, disparo, recarga, zombies con NavMesh,
rondas que escalan, puntos y compra de munición. Cámara con interruptor primera/tercera persona.

El proyecto **genera su propia escena de prueba por código** (suelo, paredes, jugador, zombies, UI),
así que se puede compilar a APK sin abrir el editor de Unity.

## APK automático con GitHub Actions

Cada `push` a `main` (o el botón **Run workflow** en la pestaña Actions) compila el APK y lo deja
como artefacto `zombies-apk` en la ejecución del workflow.

Antes de la primera vez hay que dar la licencia de Unity al CI. En el repo:
**Settings → Secrets and variables → Actions → New repository secret**, y crea:

| Secreto | Contenido |
|---|---|
| `UNITY_EMAIL` | Correo de tu cuenta de Unity |
| `UNITY_PASSWORD` | Contraseña de tu cuenta de Unity |
| `UNITY_LICENSE` | Contenido del archivo `.ulf` de licencia Personal |

La forma de obtener el `.ulf` (activación manual de la licencia Personal) está en la documentación
de GameCI: https://game.ci/docs/github/activation

Instalar el APK: descarga el artefacto, descomprímelo, pasa `zombies.apk` al celular y permite
"instalar apps de origen desconocido".

## Abrir en Unity (opcional)
1. Unity Hub → Add project from disk → esta carpeta, con **Unity 2022.3.45f1** + módulo Android.
2. Menú **Zombies → Generar escena**, abre `Assets/Scenes/Main.unity` y dale Play.
   En el editor se controla con WASD + ratón, clic izquierdo dispara.

## Estructura
- `Assets/Scripts`: jugador, arma, zombie, rondas, puntos, compra de munición, entrada táctil.
- `Assets/Editor/BuildScript.cs`: genera la escena y compila el APK (`BuildScript.Build`).
- `.github/workflows/build-apk.yml`: flujo de compilación.

## Siguientes pasos
- Modelos y animaciones de zombie (Mixamo) y armas con licencia libre.
- Barricadas en ventanas, Mystery Box, perks, más armas.
- Optimizar: pool de zombies, calidad baja/media para celulares modestos.
