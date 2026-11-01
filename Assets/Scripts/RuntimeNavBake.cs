using UnityEngine;
using Unity.AI.Navigation;

// Genera el NavMesh al iniciar la partida (así no hace falta hornearlo a mano).
[RequireComponent(typeof(NavMeshSurface))]
public class RuntimeNavBake : MonoBehaviour
{
    void Awake() { GetComponent<NavMeshSurface>().BuildNavMesh(); }
}
