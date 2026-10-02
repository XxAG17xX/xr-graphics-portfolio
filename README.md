<p align="center">
  <img src="media/banner.jpg" width="100%" alt="XR and Graphics Portfolio: frames from the scan, Blender render, hand tracking, MetaHuman, face mesh and stereo rendering projects">
</p>

<p align="center">
  <b>Take something from the real world, get it into an engine, and make it look and behave right.</b><br>
  Kartik Gupta · Trinity College Dublin, M.A.I. Computer Engineering · Extended Reality, spring 2026 (85, Distinction)
</p>

---

## The Projects

<table>
<tr>
<td width="33%" align="center"><a href="dublin-landmark-scan"><img src="media/scan_orbit.gif" width="100%" alt="Scanned Luke Kelly sculpture orbiting in Unity"></a><br><b>Dublin Landmark Scan</b><br><sub>150 photos to a 142k-triangle model, in Unity and AR</sub></td>
<td width="33%" align="center"><a href="image-to-3d-blender"><img src="media/relics_orbit.gif" width="100%" alt="Five generated relics in a Blender Cycles render"></a><br><b>Image to 3D in Blender</b><br><sub>5 generated props, 17 lights, Cycles</sub></td>
<td width="33%" align="center"><a href="ar-hand-tracking"><img src="media/hand_tracking.gif" width="100%" alt="Grabbing a virtual cube with a tracked hand"></a><br><b>AR Hand Tracking</b><br><sub>pinch, carry and throw in 3D, 18 to 30 FPS</sub></td>
</tr>
<tr>
<td align="center"><a href="metahuman-digital-double"><img src="media/metahuman.gif" width="100%" alt="MetaHuman animated from the author's voice"></a><br><b>MetaHuman Digital Double</b><br><sub>my face scan, rigged in Unreal Engine 5.6</sub></td>
<td align="center"><a href="face-mesh-tracking"><img src="media/face_mesh.gif" width="100%" alt="Face mesh tracked on a stylised cartoon face"></a><br><b>Face Mesh Tracking</b><br><sub>human, cartoon, emoji and animal faces</sub></td>
<td align="center"><a href="stereo-anaglyph-rendering"><img src="media/anaglyph.gif" width="100%" alt="Red-cyan anaglyph stereo rendering"></a><br><b>Anaglyph Stereo Rendering</b><br><sub>toe-in vs off-axis cameras, C++/OpenGL</sub></td>
</tr>
<tr>
<td align="center"><a href="photogrammetry-colmap"><img src="media/tile_photogrammetry.jpg" width="100%" alt="Dense point cloud from COLMAP"></a><br><b>Photogrammetry with COLMAP</b><br><sub>64/64 photos registered, 1.96M-triangle mesh</sub></td>
<td align="center"><a href="ai-story-booklet"><img src="media/tile_booklet.jpg" width="100%" alt="Cover of the Relics of the Void booklet"></a><br><b>AI Story Booklet</b><br><sub>5 generated images built to become 3D</sub></td>
<td align="center"><a href="unity-image-target-ar"><img src="media/image_target_ar.gif" width="100%" alt="A virtual cube tracked on an image target"></a><br><b>Image-Target AR in Unity</b><br><sub>tracking tested against size and light</sub></td>
</tr>
</table>

---

## How They Fit Together

```mermaid
flowchart LR
    A["<b>Capture</b><br/>phone photos · face scan<br/>webcam · my voice"]:::cap --> B["<b>Reconstruct and generate</b><br/>COLMAP · RealityScan<br/>TRELLIS.2 · MetaHuman"]:::gen
    B --> C["<b>Build in an engine</b><br/>Unity · Unreal Engine 5.6<br/>Blender · OpenGL"]:::eng
    C --> D["<b>Interact and present</b><br/>AR · hand tracking<br/>stereo 3D · Cycles renders"]:::out
    classDef cap fill:#1f6feb,stroke:#58a6ff,color:#fff
    classDef gen fill:#8957e5,stroke:#bc8cff,color:#fff
    classDef eng fill:#bf4b8a,stroke:#ff7bbd,color:#fff
    classDef out fill:#238636,stroke:#3fb950,color:#fff
```

## From 2D Concept to 3D Scene

<p align="center">
  <img src="media/compare_relics.jpg" width="100%" alt="Five generated concept images above the same five relics rendered in 3D">
</p>

I designed the [story booklet's](ai-story-booklet) images to be clean inputs for image-to-3D, then [generated, staged and lit](image-to-3d-blender) the same five relics in Blender.

---

## Contents

| Project | What I built | Tools |
|---|---|---|
| [Dublin Landmark Scan](dublin-landmark-scan) | A sculpture scanned from 150 photos, cleaned from a 26M-triangle scan to a 142k-triangle model, shown with an orbit camera and in AR | RealityScan, Blender, Unity, Vuforia, C# |
| [Image to 3D in Blender](image-to-3d-blender) | Five generated relics normalised, staged on a ring, lit with 17 lights and rendered as a 240-frame orbit | TRELLIS.2, Blender 5, Cycles |
| [AR Hand Tracking](ar-hand-tracking) | Two-hand tracking that lets you pinch, carry and throw a virtual cube in 3D | Python, MediaPipe, OpenCV, OpenGL |
| [MetaHuman Digital Double](metahuman-digital-double) | A rigged MetaHuman built from a scan of my face, animated from my own voice | Unreal Engine 5.6, MetaHuman Animator |
| [Face Mesh Tracking](face-mesh-tracking) | Face-mesh tracking over video, stress-tested on human, cartoon, emoji and animal faces | Python, MediaPipe, OpenCV |
| [Anaglyph Stereo Rendering](stereo-anaglyph-rendering) | Toe-in and off-axis stereo cameras, two-pass red-cyan rendering and a 100-object depth scene | C++, OpenGL, GLM |
| [Photogrammetry with COLMAP](photogrammetry-colmap) | A 64-photo object scan: every image registered at 1.29 px error, a 447k-point dense cloud, a 1.96M-triangle mesh | COLMAP |
| [AI Story Booklet](ai-story-booklet) | A five-page illustrated story with prompts designed to feed image-to-3D | Gemini (Nano Banana Pro) |
| [Image-Target AR in Unity](unity-image-target-ar) | A first image-target AR scene, with tests of target size and lighting on tracking | Unity, Vuforia |

---

## Related

- **[ARIA](https://github.com/XxAG17xX/ARIA)**: voice to generative 3D in mixed reality on a Meta Quest 3, the final project of the same module ([demo video](https://www.youtube.com/watch?v=2N-jfHEKipg)).
- **[VR Lunar South Pole](https://github.com/XxAG17xX/VR-LunarSouthPole)**: my final-year project, a walkable lunar south pole from NASA elevation data on a standalone headset ([walkthrough](https://youtu.be/z2SDj-kG6RA)).

---

<details>
<summary><b>Notes on what is and isn't here</b></summary>

- Each project folder summarises what was asked; where work started from a provided template, the folder says which parts are mine.
- Large raw data (the 26M-triangle dense mesh, full-resolution photo sets, COLMAP databases) is left out; the folders keep the final outputs and a sample of the inputs.
- Licence keys and other private settings were removed before publishing.

</details>
