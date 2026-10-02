using UnityEditor;
using UnityEngine;

public class OrbitalRotation : MonoBehaviour
{
    
  
      public float speed = 20f; 
    
    
    void Update()
    {
    transform.Rotate(0f,speed * Time.deltaTime, 0f);
    }
}
