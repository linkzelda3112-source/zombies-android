using UnityEngine;
using UnityEngine.EventSystems;

// Botón de disparo: mantiene Fire activo mientras está presionado.
public class HoldButton : MonoBehaviour, IPointerDownHandler, IPointerUpHandler
{
    public void OnPointerDown(PointerEventData e) { if (TouchInput.I) TouchInput.I.Fire = true; }
    public void OnPointerUp(PointerEventData e) { if (TouchInput.I) TouchInput.I.Fire = false; }
}
