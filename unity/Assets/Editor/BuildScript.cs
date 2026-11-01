using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.Events;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using Unity.AI.Navigation;

// Genera la escena de prueba por código y compila el APK.
// Menú: Zombies > Generar escena.  CI: -executeMethod BuildScript.Build
public static class BuildScript
{
    const string ScenePath = "Assets/Scenes/Main.unity";

    [MenuItem("Zombies/Generar escena")]
    public static void GenerateScene()
    {
        EnsureFolder("Assets/Scenes");
        EnsureFolder("Assets/Materials");
        EnsureFolder("Assets/Prefabs");

        var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
        var cam = Camera.main;

        Material floorMat = Mat("Floor", new Color(0.25f, 0.25f, 0.28f));
        Material wallMat = Mat("Wall", new Color(0.4f, 0.35f, 0.3f));
        Material zombieMat = Mat("Zombie", new Color(0.3f, 0.55f, 0.25f));
        Material headMat = Mat("ZombieHead", new Color(0.45f, 0.65f, 0.35f));
        Material playerMat = Mat("Player", new Color(0.2f, 0.35f, 0.7f));
        Material buyMat = Mat("WallBuy", new Color(0.8f, 0.6f, 0.1f));

        // ---- Suelo + NavMesh en runtime
        var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
        floor.name = "Floor";
        floor.transform.localScale = new Vector3(10, 1, 10);   // 100 x 100 m
        floor.GetComponent<Renderer>().sharedMaterial = floorMat;
        floor.AddComponent<NavMeshSurface>();
        floor.AddComponent<RuntimeNavBake>();

        // ---- Paredes del perímetro y obstáculos
        var walls = new GameObject("Walls");
        MakeWall(walls.transform, wallMat, new Vector3(0, 2, 50), new Vector3(100, 4, 1));
        MakeWall(walls.transform, wallMat, new Vector3(0, 2, -50), new Vector3(100, 4, 1));
        MakeWall(walls.transform, wallMat, new Vector3(50, 2, 0), new Vector3(1, 4, 100));
        MakeWall(walls.transform, wallMat, new Vector3(-50, 2, 0), new Vector3(1, 4, 100));
        MakeWall(walls.transform, wallMat, new Vector3(10, 1.5f, 8), new Vector3(8, 3, 2));
        MakeWall(walls.transform, wallMat, new Vector3(-12, 1.5f, -6), new Vector3(2, 3, 10));
        MakeWall(walls.transform, wallMat, new Vector3(15, 1.5f, -18), new Vector3(10, 3, 2));
        MakeWall(walls.transform, wallMat, new Vector3(-20, 1.5f, 20), new Vector3(6, 3, 6));

        // ---- Jugador
        var player = new GameObject("Player");
        player.transform.position = new Vector3(0, 1.05f, 0);
        var cc = player.AddComponent<CharacterController>();
        cc.height = 2f; cc.radius = 0.4f;
        var body = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        body.name = "Body";
        Object.DestroyImmediate(body.GetComponent<Collider>());
        body.transform.SetParent(player.transform, false);
        body.GetComponent<Renderer>().sharedMaterial = playerMat;
        var pivot = new GameObject("CameraPivot");
        pivot.transform.SetParent(player.transform, false);
        pivot.transform.localPosition = new Vector3(0, 0.6f, 0);
        cam.transform.SetParent(pivot.transform, false);
        cam.transform.localPosition = Vector3.zero;
        cam.transform.localRotation = Quaternion.identity;
        var pc = player.AddComponent<PlayerController>();
        pc.cameraPivot = pivot.transform; pc.cam = cam;
        var weapon = player.AddComponent<Weapon>();
        weapon.cam = cam;
        var stats = player.AddComponent<PlayerStats>();
        SetLayerRecursively(player, 2);   // "Ignore Raycast": los disparos no chocan con el jugador

        // ---- Entrada táctil
        new GameObject("Input").AddComponent<TouchInput>();

        // ---- Compra de munición en pared
        var buy = GameObject.CreatePrimitive(PrimitiveType.Cube);
        buy.name = "WallBuy";
        buy.transform.position = new Vector3(0, 1.5f, 12);
        buy.transform.localScale = new Vector3(3, 2, 0.3f);
        buy.GetComponent<Renderer>().sharedMaterial = buyMat;
        var wb = buy.AddComponent<WallBuy>();

        // ---- Prefab de zombie
        var zRoot = new GameObject("Zombie");
        var agent = zRoot.AddComponent<NavMeshAgent>();
        agent.radius = 0.4f; agent.height = 2f; agent.stoppingDistance = 1.2f; agent.acceleration = 20f;
        zRoot.AddComponent<Zombie>();
        var zBody = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        zBody.name = "Body";
        zBody.transform.SetParent(zRoot.transform, false);
        zBody.transform.localPosition = new Vector3(0, 1f, 0);
        zBody.GetComponent<Renderer>().sharedMaterial = zombieMat;
        var zHead = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        zHead.name = "Head";
        zHead.transform.SetParent(zRoot.transform, false);
        zHead.transform.localPosition = new Vector3(0, 1.85f, 0);
        zHead.transform.localScale = Vector3.one * 0.5f;
        zHead.GetComponent<Renderer>().sharedMaterial = headMat;
        var zPrefab = PrefabUtility.SaveAsPrefabAsset(zRoot, "Assets/Prefabs/Zombie.prefab");
        Object.DestroyImmediate(zRoot);

        // ---- Spawns y rondas
        var spawns = new GameObject("SpawnPoints");
        var pts = new Transform[4];
        Vector3[] pos = { new Vector3(40, 0, 40), new Vector3(-40, 0, 40), new Vector3(40, 0, -40), new Vector3(-40, 0, -40) };
        for (int i = 0; i < 4; i++)
        {
            var s = new GameObject("Spawn" + i);
            s.transform.SetParent(spawns.transform, false);
            s.transform.position = pos[i];
            pts[i] = s.transform;
        }
        var wm = new GameObject("Waves").AddComponent<WaveManager>();
        wm.zombiePrefab = zPrefab;
        wm.spawnPoints = pts;

        // ---- UI
        var eventSystem = new GameObject("EventSystem", typeof(EventSystem), typeof(StandaloneInputModule));
        var canvasGO = new GameObject("Canvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
        var canvas = canvasGO.GetComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        var scaler = canvasGO.GetComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1920, 1080);
        scaler.matchWidthOrHeight = 0.5f;
        var ct = canvasGO.transform;

        stats.pointsText = MakeText(ct, "Puntos", "500", new Vector2(0, 1), new Vector2(40, -40), 64, TextAnchor.UpperLeft);
        stats.healthText = MakeText(ct, "Vida", "100", new Vector2(0, 0), new Vector2(40, 40), 64, TextAnchor.LowerLeft);
        weapon.ammoText = MakeText(ct, "Municion", "30 / 120", new Vector2(1, 0), new Vector2(-40, 340), 56, TextAnchor.LowerRight);
        wm.roundText = MakeText(ct, "Ronda", "0", new Vector2(0.5f, 1), new Vector2(0, -30), 96, TextAnchor.UpperCenter);

        var fire = MakeButton(ct, "BtnFuego", "FUEGO", new Vector2(1, 0), new Vector2(-220, 220), new Vector2(240, 240));
        fire.gameObject.AddComponent<HoldButton>();
        var reload = MakeButton(ct, "BtnRecargar", "RECARGAR", new Vector2(1, 0), new Vector2(-500, 130), new Vector2(200, 130));
        UnityEventTools.AddVoidPersistentListener(reload.onClick, weapon.Reload);
        var toggle = MakeButton(ct, "BtnCamara", "CAMARA", new Vector2(1, 1), new Vector2(-130, -90), new Vector2(200, 100));
        UnityEventTools.AddVoidPersistentListener(toggle.onClick, pc.ToggleCamera);
        var buyBtn = MakeButton(ct, "BtnComprar", "COMPRAR", new Vector2(1, 0), new Vector2(-500, 290), new Vector2(200, 130));
        UnityEventTools.AddVoidPersistentListener(buyBtn.onClick, wb.TryBuy);

        var over = new GameObject("GameOver", typeof(RectTransform), typeof(Image));
        over.transform.SetParent(ct, false);
        var rt = over.GetComponent<RectTransform>();
        rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one; rt.offsetMin = rt.offsetMax = Vector2.zero;
        over.GetComponent<Image>().color = new Color(0, 0, 0, 0.75f);
        over.GetComponent<Image>().raycastTarget = false;
        var overText = MakeText(over.transform, "Texto", "GAME OVER", new Vector2(0.5f, 0.5f), Vector2.zero, 140, TextAnchor.MiddleCenter);
        overText.color = new Color(0.8f, 0.1f, 0.1f);
        over.SetActive(false);
        stats.gameOverPanel = over;

        EditorSceneManager.SaveScene(scene, ScenePath);
        AssetDatabase.SaveAssets();
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
    }

    public static void Build()
    {
        GenerateScene();

        PlayerSettings.companyName = "Zombies";
        PlayerSettings.productName = "Zombies Android";
        PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, "com.zombies.game");
        PlayerSettings.defaultInterfaceOrientation = UIOrientation.LandscapeLeft;
        PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
        PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
        PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel24;
        EditorUserBuildSettings.buildAppBundle = false;

        string dir = "build/Android";
        var args = System.Environment.GetCommandLineArgs();
        for (int i = 0; i < args.Length - 1; i++)
            if (args[i] == "-customBuildPath") dir = args[i + 1];
        Directory.CreateDirectory(dir);

        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
        {
            scenes = new[] { ScenePath },
            locationPathName = Path.Combine(dir, "zombies.apk"),
            target = BuildTarget.Android,
            options = BuildOptions.None
        });
        if (report.summary.result != BuildResult.Succeeded) EditorApplication.Exit(1);
    }

    // ---------- helpers ----------
    static void EnsureFolder(string path)
    {
        if (AssetDatabase.IsValidFolder(path)) return;
        AssetDatabase.CreateFolder(Path.GetDirectoryName(path).Replace('\\', '/'), Path.GetFileName(path));
    }

    static Material Mat(string name, Color c)
    {
        var m = new Material(Shader.Find("Standard")) { color = c };
        AssetDatabase.CreateAsset(m, "Assets/Materials/" + name + ".mat");
        return m;
    }

    static void MakeWall(Transform parent, Material m, Vector3 pos, Vector3 size)
    {
        var w = GameObject.CreatePrimitive(PrimitiveType.Cube);
        w.name = "Wall";
        w.transform.SetParent(parent, false);
        w.transform.position = pos;
        w.transform.localScale = size;
        w.GetComponent<Renderer>().sharedMaterial = m;
    }

    static void SetLayerRecursively(GameObject go, int layer)
    {
        go.layer = layer;
        foreach (Transform t in go.transform) SetLayerRecursively(t.gameObject, layer);
    }

    static Text MakeText(Transform parent, string name, string txt, Vector2 anchor, Vector2 pos, int size, TextAnchor align)
    {
        var go = new GameObject(name, typeof(RectTransform), typeof(Text));
        go.transform.SetParent(parent, false);
        var rt = go.GetComponent<RectTransform>();
        rt.anchorMin = rt.anchorMax = rt.pivot = anchor;
        rt.anchoredPosition = pos;
        rt.sizeDelta = new Vector2(700, size * 1.4f);
        var t = go.GetComponent<Text>();
        t.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        t.text = txt; t.fontSize = size; t.alignment = align; t.color = Color.white;
        t.horizontalOverflow = HorizontalWrapMode.Overflow;
        t.raycastTarget = false;
        return t;
    }

    static Button MakeButton(Transform parent, string name, string label, Vector2 anchor, Vector2 pos, Vector2 size)
    {
        var go = new GameObject(name, typeof(RectTransform), typeof(Image), typeof(Button));
        go.transform.SetParent(parent, false);
        var rt = go.GetComponent<RectTransform>();
        rt.anchorMin = rt.anchorMax = rt.pivot = anchor;
        rt.anchoredPosition = pos; rt.sizeDelta = size;
        go.GetComponent<Image>().color = new Color(1, 1, 1, 0.35f);
        var t = MakeText(go.transform, "Texto", label, new Vector2(0.5f, 0.5f), Vector2.zero, 34, TextAnchor.MiddleCenter);
        t.GetComponent<RectTransform>().sizeDelta = size;
        return go.GetComponent<Button>();
    }
}
