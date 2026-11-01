using System.Collections;
using UnityEngine;
using UnityEngine.UI;

// Rondas estilo Zombies: cada ronda hay más zombies y con más vida.
public class WaveManager : MonoBehaviour
{
    public static WaveManager I;
    public GameObject zombiePrefab;
    public Transform[] spawnPoints;
    public Text roundText;
    public float timeBetweenRounds = 8f;
    public float spawnInterval = 1.5f;
    public int maxAlive = 24;

    int round = 0;
    int toSpawn;
    int alive;
    int remaining;

    void Awake() { I = this; }
    void Start() { StartCoroutine(RoundLoop()); }

    IEnumerator RoundLoop()
    {
        while (true)
        {
            yield return new WaitForSeconds(timeBetweenRounds);
            round++;
            if (roundText) roundText.text = round.ToString();

            // Más zombies cada ronda
            toSpawn = Mathf.RoundToInt(6 + round * 3.5f);
            remaining = toSpawn;

            // Vida: +100 por ronda hasta la 9, luego x1.1 por ronda (similar a CoD)
            float hp = round < 10 ? 100 + (round - 1) * 100 : 900 * Mathf.Pow(1.1f, round - 9);
            hp = Mathf.Min(hp, 5000f);
            // Velocidad: camina al inicio, corre después
            float speed = Mathf.Lerp(1.5f, 4.5f, Mathf.Clamp01((round - 1) / 12f));

            while (toSpawn > 0)
            {
                if (alive < maxAlive) { Spawn(hp, speed); toSpawn--; }
                yield return new WaitForSeconds(spawnInterval);
            }
            while (remaining > 0) yield return null;
        }
    }

    void Spawn(float hp, float speed)
    {
        Transform sp = spawnPoints[Random.Range(0, spawnPoints.Length)];
        var go = Instantiate(zombiePrefab, sp.position, sp.rotation);
        go.GetComponent<Zombie>().Setup(hp, speed);
        alive++;
    }

    public void ZombieDied() { alive--; remaining--; }
}
