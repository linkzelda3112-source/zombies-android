using UnityEngine;
using UnityEngine.AI;

// Zombie que persigue al jugador con NavMesh. Requiere NavMeshAgent y Collider.
// Para headshots: pon un collider hijo en la cabeza llamado "Head".
[RequireComponent(typeof(NavMeshAgent))]
public class Zombie : MonoBehaviour
{
    public float health = 100f;
    public float attackDamage = 20f;
    public float attackRange = 1.6f;
    public float attackCooldown = 1f;
    public int pointsPerHit = 10;
    public int pointsPerKill = 60;
    public int pointsPerHeadshotKill = 100;
    public Animator animator;            // opcional: parámetros "Speed" (float) y "Attack" (trigger)

    NavMeshAgent agent;
    Transform player;
    float nextAttack;
    bool dead;

    void Awake() { agent = GetComponent<NavMeshAgent>(); }

    void Start()
    {
        player = PlayerStats.I.transform;
    }

    // Lo llama el WaveManager al spawnear
    public void Setup(float hp, float speed)
    {
        health = hp;
        agent.speed = speed;
    }

    void Update()
    {
        if (dead || player == null) return;
        agent.SetDestination(player.position);

        float dist = Vector3.Distance(transform.position, player.position);
        if (animator) animator.SetFloat("Speed", agent.velocity.magnitude);

        if (dist <= attackRange && Time.time >= nextAttack)
        {
            nextAttack = Time.time + attackCooldown;
            if (animator) animator.SetTrigger("Attack");
            PlayerStats.I.TakeDamage(attackDamage);
        }
    }

    public void TakeDamage(float dmg, bool headshot)
    {
        if (dead) return;
        health -= dmg;
        PlayerStats.I.AddPoints(pointsPerHit);
        if (health <= 0) Die(headshot);
    }

    void Die(bool headshot)
    {
        dead = true;
        agent.enabled = false;
        PlayerStats.I.AddPoints(headshot ? pointsPerHeadshotKill : pointsPerKill);
        WaveManager.I.ZombieDied();
        Destroy(gameObject, 3f);   // aquí puedes poner animación de muerte/ragdoll
    }
}
