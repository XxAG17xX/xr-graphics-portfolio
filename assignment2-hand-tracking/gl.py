import moderngl
import moderngl_window as mglw
from pyrr import Matrix44

import cv2
import numpy as np
import os
from array import array

from prediction import predict, get_camera_matrix, get_fov_y, solvepnp


class CameraAR(mglw.WindowConfig):
    gl_version = (3, 3)
    title = "CameraAR"
    resource_dir = os.path.normpath(os.path.join(__file__, '../data'))
    previousTime = 0
    currentTime = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Shader for rendering 3D objects
        self.prog3d = self.ctx.program(
            vertex_shader='''
                #version 330

                uniform mat4 Mvp;

                in vec3 in_position;
                in vec3 in_normal;
                in vec2 in_texcoord_0;

                out vec3 v_vert;
                out vec3 v_norm;
                out vec2 v_text;

                void main() {
                    gl_Position = Mvp * vec4(in_position, 1.0);
                    v_vert = in_position;
                    v_norm = in_normal;
                    v_text = in_texcoord_0;
                }
            ''',
            fragment_shader='''
                #version 330

                uniform vec3 Color;
                uniform vec3 Light;
                uniform sampler2D Texture;
                uniform bool withTexture;

                in vec3 v_vert;
                in vec3 v_norm;
                in vec2 v_text;

                out vec4 f_color;

                void main() {
                    float lum = clamp(dot(normalize(Light - v_vert), normalize(v_norm)), 0.0, 1.0) * 0.8 + 0.2;
                    if (withTexture) {
                        f_color = vec4(Color * texture(Texture, v_text).rgb * lum, 1.0);
                    } else {
                        f_color = vec4(Color * lum, 1.0);
                    }
                }
            ''',
        )
        self.mvp = self.prog3d['Mvp']
        self.light = self.prog3d['Light']
        self.color = self.prog3d['Color']
        self.withTexture = self.prog3d['withTexture']

        # Load the 3D virtual object, and the marker for hand landmarks
        self.scene_cube = self.load_scene('crate.obj')
        self.scene_marker = self.load_scene('marker.obj')

        # Extract the VAOs from the scene
        self.vao_cube = self.scene_cube.root_nodes[0].mesh.vao.instance(self.prog3d)
        self.vao_marker = self.scene_marker.root_nodes[0].mesh.vao.instance(self.prog3d)

        # Texture of the cube
        self.texture = self.load_texture_2d('crate.png')

        # Define the initial position of the virtual object
        # The OpenGL camera is position at the origin, and look at the negative Z axis. The object is at 30 centimeters in front of the camera.
        self.object_pos = np.array([0.0, 0.0, -30.0])

        """
        --------------------------------------------------------------------
        TODO: Task 3.
        Add support to render a rectangle of window size.
        --------------------------------------------------------------------
        """
        # Simple pass-through shader, just samples the
        # webcam texture and writes it to screen.This becomes the AR background layer.
        self.prog_quad = self.ctx.program(
            vertex_shader='''
                #version 330
                in vec2 in_vert;
                in vec2 in_texcoord;
                out vec2 v_texcoord;
                void main() {
                    gl_Position = vec4(in_vert, 0.0, 1.0);
                    v_texcoord = in_texcoord;
                }
            ''',
            fragment_shader='''
                #version 330
                uniform sampler2D Texture;
                in vec2 v_texcoord;
                out vec4 f_color;
                void main() {
                    f_color = texture(Texture, v_texcoord);
                }
            ''',
        )

        # Two triangles covering NDC [-1, 1] — fills the entire screen.
        # Each vertex is (x, y, u, v). The V coordinate is flipped because OpenCV's
        # origin is top-left while OpenGL's is bottom-left; without this the video
        # would render upside down.
        quad_vertices = np.array([
            -1.0,  1.0,  0.0,  0.0,
            -1.0, -1.0,  0.0,  1.0,
             1.0, -1.0,  1.0,  1.0,
            -1.0,  1.0,  0.0,  0.0,
             1.0, -1.0,  1.0,  1.0,
             1.0,  1.0,  1.0,  0.0,
        ], dtype='f4')

        self.vbo_quad = self.ctx.buffer(quad_vertices)
        self.vao_quad = self.ctx.vertex_array(
            self.prog_quad,
            [(self.vbo_quad, '2f 2f', 'in_vert', 'in_texcoord')]
        )
        # Start OpenCV camera
        self.capture = cv2.VideoCapture(0)

        # Webcam will use my closest supported resolution.
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # Get a frame to set the window size and aspect ratio
        ret, frame = self.capture.read()
        self.aspect_ratio = float(frame.shape[1]) / frame.shape[0]
        self.window_size = (frame.shape[1],frame.shape[0])

        # GPU texture that gets overwritten every frame with the webcam image.
        # Created after window_size is known so the dimensions are correct.
        self.video_texture = self.ctx.texture(self.window_size, 3)
        self.video_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        """
        --------------------------------------------------------------------
        TODO: Task 5.
        We detect a simple pinch gesture, and check if the index finger hits
        the cube. We approximate by just checking the finger tip is close
        enough to the cube location.
        --------------------------------------------------------------------
        """
        # All thresholds are in centimetres to match the x100 OpenGL world space units.
        self.PINCH_THRESHOLD = 3.5  # thumb-to-index tip distance that counts as a pinch
        self.GRAB_THRESHOLD = 10  # pinch midpoint must be within this distance of the cube

        # Per-hand pinch state for hysteresis — once pinching, fingers must open to
        # 1.4x the threshold before releasing, which kills flickering at the boundary.
        self.is_pinching  = [False, False]
        self.pinch_dist_smooth = [0.0, 0.0]

        # Grab state — which hand is holding the cube and the positional offset recorded
        # at grab time so the cube doesn't snap to the finger midpoint on pickup.
        self.grabbed  = False
        self.grab_hand_idx = -1
        self.grab_offset  = np.zeros(3)

        # Throw state — velocity is tracked frame-to-frame while grabbed so that on
        # release the cube takes the hand's motion and flies off naturally.
        # Friction of 0.92 per frame models air resistance and brings it to rest.
        self.velocity   = np.zeros(3)
        self.prev_pinch_pos = None
        self.FRICTION    = 0.92
        self.MIN_VELOCITY   = 0.05  # below this the cube is considered at rest

        # After a reset fires,ignore the gesture for 30 frames so it doesn't
        # keep triggering while the hand is still held in the peace-sign shape.
        self.reset_cooldown   = 0
        self.RESET_COOLDOWN_FRAMES = 30

        # Rolling FPS window — averaging over 30 timestamps gives a stable readout
        # that doesn't jitter with each individual frame.
        self.fps_times   = []
        self.fps_window  = 30
        self.fps_display = 0.0

    
    # Gesture helpers
    

    def _detect_pinch(self, gl_landmarks, hand_idx):
        """
        Measures the 3D distance between thumb tip (4) and index tip (8) in OpenGL
        world space (centimetres). Returns whether the hand is pinching,the midpoint
        between those two tips,the raw distance,and just_pinched.

        just_pinched is True only on the single frame the pinch first engages.
        The grab logic uses this so the user must actively close their fingers while
        already near the cube— pre-pinching and walking toward it won't trigger a grab,
        it is too wonky otherwise if the cube is already in grab range and the user 
        just walks into the pinch pose by accident.
        
        Hysteresis:engage needs dist < PINCH_THRESHOLD, release needs dist > 1.4 times that.
        This prevents the pinch state flickering when fingers hover at the boundary.
        """
        thumb_tip = gl_landmarks[4]
        index_tip = gl_landmarks[8]
        dist   = np.linalg.norm(thumb_tip - index_tip)
        self.pinch_dist_smooth[hand_idx] = 0.4 * dist + 0.6 * self.pinch_dist_smooth[hand_idx]
        dist = self.pinch_dist_smooth[hand_idx]
        midpoint  = (thumb_tip + index_tip) / 2.0

        prev_state  = self.is_pinching[hand_idx]
        threshold  = self.PINCH_THRESHOLD * 1.4 if prev_state else self.PINCH_THRESHOLD
        self.is_pinching[hand_idx] = dist < threshold
        just_pinched  = self.is_pinching[hand_idx] and not prev_state

        return self.is_pinching[hand_idx], midpoint, dist, just_pinched

    def _detect_peace_sign(self, gl_landmarks):
        """
        Checks for a peace / victory sign: index (8) and middle (12) extended above
        their base knuckles (5, 9),while ring (16),pinky (20) and thumb (4) are
        curled below theirs(13, 17, 5).All Y comparisons in OpenGL space(up = +Y axis).

        Its chosen as the reset gesture because its visually distinct from a pinch and
        won't fire accidentally during normal grab or throw interactions.
        """
        idx_up = gl_landmarks[8][1] > gl_landmarks[5][1]
        mid_up = gl_landmarks[12][1]> gl_landmarks[9][1]
        ring_dn = gl_landmarks[16][1]< gl_landmarks[13][1]
        pink_dn = gl_landmarks[20][1]< gl_landmarks[17][1]
        thumb_dn = gl_landmarks[4][1] < gl_landmarks[5][1]
        return idx_up and mid_up and ring_dn and pink_dn and thumb_dn

    def _apply_bounds_with_bounce(self, fov_y):
        """
        Keeps the cube inside the visible screen volume so it can never fly off-screen.

        Rather than fixed X/Y limits, the visible half-extents at the cube's current
        depth are computed from the perspective projection formula:
        
            half_h = tan(fov/2) * |Z|,   half_w = half_h * aspect_ratio
            (How I got this?...)
            (https://www.lighthouse3d.com/tutorials/view-frustum-culling/view-frustums-shape/)
        This means the boundary exactly matches screen edges at any depth — the cube
        gets tighter world-space limits the further away it is.

        On contact, velocity is reflected and damped by 0.4 to simulate a soft bounce.
        Z is clamped to [-100, -5] to keep the cube in front of the camera at all times.
        """
        z  = abs(self.object_pos[2])
        half_h = np.tan(np.radians(fov_y / 2.0)) * z
        half_w = half_h * self.aspect_ratio
        bounds = [(-half_w, half_w), (-half_h, half_h), (-100.0, -5.0)]

        for axis, (lo, hi) in enumerate(bounds):
            if self.object_pos[axis] < lo:
                self.object_pos[axis] = lo
                self.velocity[axis]   =  abs(self.velocity[axis]) * 0.4
            elif self.object_pos[axis] > hi:
                self.object_pos[axis] = hi
                self.velocity[axis]   = -abs(self.velocity[axis]) * 0.4

    def _draw_hud(self, frame, pinch_info, grabbed, resetting, handedness_list):
        """
        Draws the HUD directly onto the OpenCV frame before GPU upload, so it gets
        baked into the video texture at zero extra OpenGL render cost.

        Shows FPS colour-coded against the 10fps assignment threshold,per-hand
        Left/Right label with DistToObject(the exact value driving grab decisions),
        interaction state,and a gesture hint at the bottom.
        """
        h, w = frame.shape[:2]

        # Green >=20fps, yellow >=10fps (assignment minimum), red <10fps
        fps  = self.fps_display
        fps_color = (0, 255, 0) if fps >= 20 else (0, 200, 255) if fps >= 10 else (0, 0, 255)
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, fps_color, 2)

        for i,(is_pinching, midpoint, dist, hand_idx, just_pinched) in enumerate(pinch_info):
            if handedness_list and i < len(handedness_list) and handedness_list[i]:
                # MediaPipe reports handedness relative to the un-flipped image, but the
                # frame is flipped before detection, so Left and Right need to be swapped.
                raw   = handedness_list[i][0].display_name
                label = "Right" if raw == "Left" else "Left"
            else:
                label = "Hand"

            # DistToObject is the full 3D Euclidean distance — X, Y and Z all contribute,
            # so depth is fully accounted for. This is exactly what the grab check uses.
            dist_to_cube = np.linalg.norm(midpoint - self.object_pos)
            color  = (0, 255, 0) if is_pinching else (255, 255, 255)
            y     = 60 + i * 55
            cv2.putText(frame, f"{label} - Pinched: {is_pinching}", (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            cv2.putText(frame, f"  DistToObject: {dist_to_cube:.2f}", (10, y + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        y_state = 60 + len(pinch_info) * 55 + 10
        if resetting:
            state, state_color = "RESET",(0, 255, 255)
        elif grabbed:
            state, state_color = "GRABBED",(0, 100, 255)
        elif np.linalg.norm(self.velocity) > self.MIN_VELOCITY:
            state, state_color = "THROW",(0, 165, 255)
        else:
            state, state_color = "IDLE",(255, 255, 255)
        cv2.putText(frame, f"State: {state}", (10, y_state),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, state_color, 2)

        cv2.putText(frame, "Pinch near cube=grab/throw  Peace sign=reset",
                    (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

        return frame

    # Main render loop
    
    def on_render(self, time: float, frame_time: float):
        self.ctx.clear(1.0, 1.0, 1.0)
        self.ctx.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)

        # Rolling window of timestamps gives a smoother FPS display than using
        # frame_time directly, which fluctuates too much frame-to-frame.
        import time as _time
        now = _time.perf_counter()
        self.fps_times.append(now)
        if len(self.fps_times) > self.fps_window:
            self.fps_times.pop(0)
        if len(self.fps_times) >= 2:
            elapsed = self.fps_times[-1] - self.fps_times[0]
            if elapsed > 0:
                self.fps_display = (len(self.fps_times) - 1) / elapsed

        if self.reset_cooldown > 0:
            self.reset_cooldown -= 1

        """
        ---------------------------------------------------------------
        TODO: Task 3.
        Get OpenCV video frame, display in OpenGL.
        Render the frame to a screen-sized rectangle.
        ---------------------------------------------------------------
        """
        ret, frame = self.capture.read()
        if not ret:
            return

        #Horizontal flip gives a natural view and ensures that
        # landmark left/right coordinates match what the user sees on screen.
        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, self.window_size)

        # Convert BGR (OpenCV default) to RGB , both OpenGL and MediaPipe expect RGB(GPT said so),
        # otherwise red and blue channels are swapped in the final render.
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        """
        ---------------------------------------------------------------
        TODO: Task 4.
        Perform hand landmark prediction, and
        solve PnP to get world landmarks list.
        ---------------------------------------------------------------
        """
        #pass directly to predict().
        detection_result = predict(frame)

        # Focal length estimated as frame_width,as
        # real calibration data is unavailable.
        frame_height, frame_width = frame.shape[:2]
        camera_matrix = get_camera_matrix(frame_width, frame_height)

        model_landmarks_list = detection_result.hand_world_landmarks if detection_result else []
        image_landmarks_list = detection_result.hand_landmarks       if detection_result else []
        handedness_list      = detection_result.handedness           if detection_result else []

        # Solving PnP to obtain world-space 3D landmarks aligned to the camera view
        world_landmarks_list =solvepnp(
            model_landmarks_list, image_landmarks_list,
            camera_matrix, frame_width, frame_height
        )

        # Solve the landmarks in world space
        # OpenCV to OpenGL conversion:
        # The world points from OpenCV need some changes to be OpenGL ready.
        # First, the model points are in meters (MediaPipe convention), while our camera matrix is in units. There exists a scale ambiguity of the true hand landmarks, i.e., if we scale up the world points by 1000, its projection remains the same (due to perspective division).
        # Here we shift the measurement from meter to centimeter, and assume our world space in OpenGL is in centimeters, just for easy visualization and object interaction. So we multiply all points by 100.
        # Second, the OpenCV and OpenGL camera coordinate system are different. OpenCV: right x, down y, into screen z. Image: right x, down y.
        # OpenGL: right x, up y, out of screen z. Image: right x, up y.
        # Check for image and 3D points flip to make sure the points are properly converted.
        gl_landmarks_list = []
        for world_landmarks in world_landmarks_list:
            gl_points = world_landmarks * 100.0
            gl_points[:, 1] *= -1 # flip Y: OpenCV down to OpenGL up
            gl_points[:, 2] *= -1  # flip Z: OpenCV into screen to OpenGL out of screen
            gl_landmarks_list.append(gl_points)

        #Clear hysteresis state for any hand that left the frame this frame,
        #so a hand re-entering doesn't inherit stale pinch state.
        for i in range(len(gl_landmarks_list), 2):
            self.is_pinching[i] = False

        # Draw red 2D circles at each raw image-space landmark position.
        # These are the Task 4 2D landmarks — exactly where MediaPipe detected each
        # joint on the image plane before any 3D reasoning. The green plus signs
        # rendered later in OpenGL are the same joints lifted into 3D via PnP.
        # When the two sets overlap on screen, the coordinate alignment is correct.
        for hand_lms in image_landmarks_list:
            for lm in hand_lms:
                px = int(lm.x * frame_width)
                py = int(lm.y * frame_height)
                cv2.circle(frame, (px, py), 4, (0, 0, 255), -1)

        """
        ----------------------------------------------------------------------
        TODO: Task 5.
        We detect a simple pinch gesture, and check if the index finger hits
        the cube. We approximate by just checking the finger tip is close
        enough to the cube location.
        ----------------------------------------------------------------------
        """
        grabbed = False

        # Peace sign resets the cube to its start position. Cooldown blocks re-firing
        # for 30 frames so the cube doesn't keep resetting while the hand is still raised.
        resetting = False
        if self.reset_cooldown == 0:
            for gl_landmarks in gl_landmarks_list:
                if self._detect_peace_sign(gl_landmarks):
                    self.object_pos     = np.array([0.0, 0.0, -30.0])
                    self.velocity       = np.zeros(3)
                    self.grabbed        = False
                    self.reset_cooldown = self.RESET_COOLDOWN_FRAMES
                    resetting           = True
                    break

        # Run pinch detection on all hands and collect results for this frame.
        # Done once here so both the grab logic and the HUD share the same data.
        pinch_info = []
        for i, gl_landmarks in enumerate(gl_landmarks_list):
            is_pinching, midpoint, pinch_dist, just_pinched = self._detect_pinch(gl_landmarks, i)
            pinch_info.append((is_pinching, midpoint, pinch_dist, i, just_pinched))

        # Grab requires just_pinched — the moment fingers first close — while already
        # within grab range. This means the user must approach with an open hand and
        # then pinch near the cube.Pre-pinching and walking toward it won't trigger
        # (as explained in the start).
        # Once grabbed, continuous pinch sustains the hold as expected.
        any_hand_grabbing = False
        for is_pinching, midpoint, pinch_dist, hand_idx, just_pinched in pinch_info:
            if not is_pinching:
                continue

            finger_to_cube = np.linalg.norm(midpoint - self.object_pos)

            if not self.grabbed:
                if just_pinched and finger_to_cube < self.GRAB_THRESHOLD:
                    self.grabbed  = True
                    self.grab_hand_idx  = hand_idx
                    #Offset recorded at grab time so the cube doesn't snap to fingers,
                    #it stays at its position relative to the hand when grabbed.
                    self.grab_offset  = self.object_pos - midpoint
                    self.prev_pinch_pos = midpoint.copy()
                    self.velocity  = np.zeros(3)
                    any_hand_grabbing = True
                    break

            elif self.grab_hand_idx == hand_idx:
                #Move cube rigidly with the hand using the recorded offset.
                self.object_pos = midpoint + self.grab_offset
                #Frame-to-frame displacement becomes the throw velocity on release.
                if self.prev_pinch_pos is not None:
                    self.velocity = midpoint - self.prev_pinch_pos
                self.prev_pinch_pos = midpoint.copy()
                any_hand_grabbing  = True
                break

        #Grabbing hand opened — release the cube, keeping velocity for the throw.
        if self.grabbed and not any_hand_grabbing:
            self.grabbed  = False
            self.grab_hand_idx = -1
            self.prev_pinch_pos = None

        #Applying residual velocity with friction after release.
        if not self.grabbed and np.linalg.norm(self.velocity) > self.MIN_VELOCITY:
            self.object_pos += self.velocity
            self.velocity *= self.FRICTION

        """
        ----------------------------------------------------------------------
        TODO: Task 4.
        Render the markers.
        ----------------------------------------------------------------------
        """
        # Note we have to set the OpenGL projection matrix by following parameters from the OpenCV camera matrix, i.e., the field of view.
        # You can use Matrix44.perspective_projection function, and set the parameters accordingly. Note that the fov must be computed based on the camera matrix. See prediction.py.


        #FOV derived from the estimated focal length so OpenGL projection matches
        #the physical camera geometry. Using a hardcoded 45° causes visible
        #misalignment between the 3D markers and the real hand in the video.
        fov_y = get_fov_y(camera_matrix, frame_height)
        proj  = Matrix44.perspective_projection(fov_y, self.aspect_ratio, 0.1, 1000)

        #Clamp cube to screen edges at its current depth; bounce velocity on contact.
        self._apply_bounds_with_bounce(fov_y)

        #Bake HUD into the frame before GPU upload.
        frame = self._draw_hud(frame, pinch_info, self.grabbed, resetting, handedness_list)

        #Upload frame (red 2D circles + HUD included) to the GPU texture.
        self.video_texture.write(np.ascontiguousarray(frame))

        #Render the video quad with depth test off so it always sits behind every
        #3D object regardless of depth buffer state.
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.video_texture.use(location=0)
        self.prog_quad['Texture'].value = 0
        self.vao_quad.render()
        self.ctx.enable(moderngl.DEPTH_TEST)

        # Translate the object to its position
        translate = Matrix44.from_translation(self.object_pos)

        # Add a bit of random rotation just to be dynamic
        rotate = Matrix44.from_y_rotation(np.sin(time) * 0.5 + 0.2)

        # Scale the object up for easy viewing
        scale = Matrix44.from_scale((3, 3, 3))

        mvp = proj * translate * rotate * scale

        #Colour feedback: red = held, orange = in-flight throw, white = idle.
        self.color.value = (1.0, 1.0, 1.0)
        if self.grabbed:  # A bit of feedback when the object is grabbed
            self.color.value = (1.0, 0.0, 0.0)
        elif np.linalg.norm(self.velocity) > self.MIN_VELOCITY:
            self.color.value = (1.0, 0.6, 0.2)

        self.light.value = (10, 10, 10)
        self.mvp.write(mvp.astype('f4'))
        self.withTexture.value = True

        # Render the object
        self.texture.use()
        self.vao_cube.render()

        # Render the landmarks
        
        #Green plus signs at every world-space landmark — yellow for the hand currently
        #holding the cube.Paired with the red 2D circles drawn earlier in OpenCV,
        #these confirm the PnP alignment:if the two sets overlap, the solve is correct.
        self.withTexture.value = False
        marker_scale = Matrix44.from_scale((0.3, 0.3, 0.3))
        for i, gl_landmarks in enumerate(gl_landmarks_list):
            self.color.value =(1.0, 1.0, 0.0) if (self.grabbed and i == self.grab_hand_idx) \
                               else (0.0, 1.0, 0.0)
                               
            for point in gl_landmarks:
                marker_translate = Matrix44.from_translation(point.tolist())
                mvp_marker = proj * marker_translate * marker_scale
                self.mvp.write(mvp_marker.astype('f4'))
                self.vao_marker.render()


if __name__ == '__main__':
    CameraAR.run()