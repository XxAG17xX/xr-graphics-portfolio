# Lab 9: Image to 3D, Staged and Lit in Blender

> The five relics from my Lab 8 booklet, generated as 3D models and rendered in Cycles

<img src="../media/lab9_relics.gif" width="100%" alt="Orbit render of the five relics">

**Render:** [render.mp4](render.mp4) (240 frames)

## What was asked
Turn the main object on each booklet page into 3D with **Microsoft TRELLIS.2**, place them all in **Blender**, and render a video.

## What I did
- Generated the five meshes with TRELLIS.2 (about **1.43 million** triangles in total, 4K textures).
- **Layout:** normalised every relic to 1.2 m and placed them on a 2.8 m ring at 72 degree steps.
- **Lighting:** **17** lights, including a light hidden inside the crystal and rim and fill lights parented to the camera so the props stay lit as it moves.
- **Shading:** emission masked by each prop's own texture, and a Light Path world shader that shows the starfield to the camera without letting it light the scene.
- **Render:** a 240-frame orbit in **Cycles** with OptiX denoising and Filmic colour.

## Files
- `relics_of_the_void.blend`: the full scene. `render.mp4`: the result. `report.pdf`: my workflow report (written before the final camera tweaks, so its camera numbers differ slightly from the file).

## What I would change
Remove a leftover lens zoom that no longer matches the orbit, move two lights that stayed behind when the seed pod moved, and clear out duplicated lights.
