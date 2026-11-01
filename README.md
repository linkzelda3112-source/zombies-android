# Zombies Starter (Android, Unity)

Base jugable de un modo Zombies por rondas: movimiento táctil, disparo, recarga, zombies con NavMesh,
rondas que escalan, puntos y compra de munición. Cámara con interruptor primera/tercera persona.

## Requisitos
- Unity 6 (o 2022 LTS) con el módulo **Android Build Support**.
- Proyecto en plantilla **3D (URP)** o 3D estándar.
- Paquete **AI Navigation** (Package Manager) para el NavMesh.

## Montaje rápido
1. Copia la carpeta `Scripts` a `Assets/Scripts`.
2. **Escenario:** crea un plano grande (suelo) y algunas paredes/cajas. Añade un componente
   **NavMesh Surface** al suelo y pulsa **Bake**.
3. **Jugador:**
   - Crea una cápsula "Player" con `CharacterController`, `PlayerController`, `PlayerStats`, `Weapon`.
   - Añade un hijo vacío "CameraPivot" a ~1.6 m de altura y pon la **Main Camera** dentro.
   - Asigna `cameraPivot` y `cam` en `PlayerController`, y `cam` en `Weapon`.
4. **Input:** crea un objeto vacío "Input" con `TouchInput`.
5. **Zombie (prefab):** cápsula o modelo con `NavMeshAgent`, `Collider`, `Zombie`.
   Para headshots: hijo con collider en la cabeza y tag `Head`.
6. **Rondas:** objeto vacío "Waves" con `WaveManager`; asigna el prefab y 3–4 puntos de spawn
   (objetos vacíos repartidos por el mapa, lejos del jugador).
7. **UI (Canvas):** textos de puntos, vida, munición y ronda; botón de disparo con EventTrigger
   (PointerDown → `TouchInput.FireDown`, PointerUp → `TouchInput.FireUp`); botón de recarga
   (`Weapon.Reload`); botón de cámara (`PlayerController.ToggleCamera`); panel de Game Over.
8. **Android:** File → Build Profiles → Android → *Switch Platform*. En Player Settings:
   Orientación = Landscape Left, Scripting Backend = IL2CPP, ARM64 activado, Min API 24.
   Conecta tu celular con depuración USB y pulsa **Build And Run**.

## Siguientes pasos
- Modelos y animaciones de zombie (Mixamo, gratis) y armas (Asset Store / Sketchfab con licencia libre).
- Barricadas en ventanas, Mystery Box, perks, más armas.
- Optimizar: pool de zombies, luces horneadas, calidad baja/media para celulares modestos.
