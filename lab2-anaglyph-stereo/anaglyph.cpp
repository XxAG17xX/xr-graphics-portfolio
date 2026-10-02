#include <glad/gl.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>

#include <render/shader.h>
#include <render/texture.h>
#include <models/box.h>

#include <vector>
#include <iostream>
#define _USE_MATH_DEFINES
#include <math.h>

static GLFWwindow *window;
static int windowWidth = 1024; 
static int windowHeight = 768;

static void key_callback(GLFWwindow *window, int key, int scancode, int action, int mode);
static void cursor_position_callback(GLFWwindow* window, double xpos, double ypos);
//mouse state
static bool mouseDragging = false;
static double lastMouseX = 0.0, lastMouseY = 0.0;
static bool usePart4Scene = true;   // Part 4 corridor scene vs random scene toggle(just for me)



// OpenGL camera view parameters
static glm::vec3 originalEyeCenter(0, 0, 100);

static glm::vec3 eyeCenter = originalEyeCenter;
static glm::vec3 lookat(0, 0, 0);
static glm::vec3 up(0, 1, 0);

static glm::float32 FoV = 45;
static glm::float32 zNear = 0.1f; 
static glm::float32 zFar = 1000.0f;

// View control 
static float viewAzimuth = M_PI / 2;
static float viewPolar = M_PI / 2;
static float viewDistance = 100.0f;
static bool rotating = false;

//to maintain the rotation centre of camera even after changing view by mouse dragging
static void updateEyeCenterFromAngles() {
	eyeCenter.x = viewDistance * sin(viewPolar) * cos(viewAzimuth);
	eyeCenter.y = viewDistance * cos(viewPolar);
	eyeCenter.z = viewDistance * sin(viewPolar) * sin(viewAzimuth);
}


// Scene control 
static int numBoxes = 1;				// Debug: set numBoxes to 1.
std::vector<glm::mat4> boxTransforms;	// We represent the scene by a single box and a number of transforms for drawing the box at different locations.

// Anaglyph control 
static float ipd = 2.0f;				// Distance between left/right eye.
// After you implement the anaglyph, adjust the IPD value to control the red/cyan offsets and depth perception. 

enum AnaglyphMode {
	None,
	ToeIn, 
	Asymmetric, 
	AnaglyphModeCount,
};

static std::string strAnaglyphMode[] = {
	"None", 
	"Toe-in", 
	"Asymmetric view frustum", 
	"Invalid",
};

static AnaglyphMode anaglyphMode = AnaglyphMode::None;

// Helper functions 

static void nextAnaglyphMode() {
	anaglyphMode = (AnaglyphMode)(((int)anaglyphMode + 1) % (int)AnaglyphModeCount);
}

static int randomInt() {
	return rand();
}

static float randomFloat() {
	float r = static_cast<float>(rand()) / static_cast<float>(RAND_MAX);
	return r;
}

static glm::vec3 randomVec3() {
	return glm::vec3(randomFloat(), randomFloat(), randomFloat());
}

static void generateScenePart4() {
	boxTransforms.clear();
	boxTransforms.reserve(numBoxes);

	auto pushBox = [&](const glm::vec3& pos, const glm::vec3& scale,
	                   float angle = 0.0f, const glm::vec3& axis = glm::vec3(0, 1, 0)) {
		glm::mat4 M(1.0f);
		M = glm::translate(M, pos);
		if (fabs(angle) > 1e-6f) M = glm::rotate(M, angle, axis);
		M = glm::scale(M, scale);
		boxTransforms.push_back(M);
	};

	//Scene design goals idea:
	// -depth references (floor + walls + back wall)
	// -near object that "pops" in toein and assymetric modes
	// -mid-depth markers to show progression
	// -random clutter just for spacing between cubes

	//Corridor anchors
	if ((int)boxTransforms.size() < numBoxes)
		pushBox(glm::vec3(0, -22, -120), glm::vec3(180, 2, 320));      // floor
	if ((int)boxTransforms.size() < numBoxes)
		pushBox(glm::vec3(-90, 0, -120), glm::vec3(2, 60, 320));       // left wall
	if ((int)boxTransforms.size() < numBoxes)
		pushBox(glm::vec3( 90, 0, -120), glm::vec3(2, 60, 320));       // right wall
	if ((int)boxTransforms.size() < numBoxes)
		pushBox(glm::vec3(0, 0, -280), glm::vec3(180, 60, 2));         // far back wall

	//Near object
	if ((int)boxTransforms.size() < numBoxes)
		pushBox(glm::vec3(0, -10, 40), glm::vec3(12, 12, 12), 0.25f);

	//Mid-depth markers:alternating left/right so parallax is visible
	for (float z = 0.0f; z >= -240.0f && (int)boxTransforms.size() < numBoxes; z -= 40.0f) {
		if ((int)boxTransforms.size() < numBoxes)
			pushBox(glm::vec3(-45, -15, z - 10), glm::vec3(8, 8, 8), 0.30f);
		if ((int)boxTransforms.size() < numBoxes)
			pushBox(glm::vec3( 45, -15, z - 30), glm::vec3(8, 8, 8), -0.25f);
	}

	// Fill remaining with small clutter inside corridor volume (kept modest on purpose)
	while ((int)boxTransforms.size() < numBoxes) {
		float x = (randomFloat() * 140.0f) - 70.0f;   // [-70, 70]
		float y = (randomFloat() * 45.0f) - 15.0f;    // [-15, 30]
		float z = (randomFloat() * 320.0f) - 260.0f;  // [-260, 60]

		float s = 2.0f + (randomFloat() * 3.0f);
		float ang = randomFloat() * (float)(2.0 * M_PI);

		pushBox(glm::vec3(x, y, z), glm::vec3(s, s, s), ang);
	}
}

static void generateScene() {
	boxTransforms.clear();

	if (numBoxes == 1) {
		// Use this for debugging
		glm::mat4 modelMatrix(1.0f);
		modelMatrix = glm::translate(modelMatrix, glm::vec3(0, 0, 0));
		modelMatrix = glm::scale(modelMatrix, glm::vec3(16, 16, 16));
		boxTransforms.push_back(modelMatrix);
		return; // IMPORTANT
	}

	if (usePart4Scene) {
		generateScenePart4();
		return;
	}

	// Random scene fallback
	for (int i = 0; i < numBoxes; ++i) {
		glm::vec3 position = 100.0f * (randomVec3() - 0.5f);
		float s = (1 + (randomInt() % 4)) * 1.0f;
		glm::vec3 scale(s, s, s);
		float angle = randomFloat() * (float)(M_PI * 2.0);
		glm::vec3 axis = glm::normalize(randomVec3() - 0.5f);

		glm::mat4 modelMatrix(1.0f);
		modelMatrix = glm::translate(modelMatrix, position);
		modelMatrix = glm::rotate(modelMatrix, angle, axis);
		modelMatrix = glm::scale(modelMatrix, scale);
		boxTransforms.push_back(modelMatrix);
	}
}



// Debugging functions 

static void printAnaglyphMode() {
	std::cout << "Anaglyph mode: " << strAnaglyphMode[(int)anaglyphMode] << std::endl;
}

static void printVec3(glm::vec3 v) {
	std::cout << v.x << " " << v.y << " " << v.z << std::endl;
}

static void printMat4(glm::mat4 m) {
	// Column major
	std::cout << m[0][0] << " " << m[1][0] << " " << m[2][0] << " " << m[3][0] << std::endl;
	std::cout << m[0][1] << " " << m[1][1] << " " << m[2][1] << " " << m[3][1] << std::endl;
	std::cout << m[0][2] << " " << m[1][2] << " " << m[2][2] << " " << m[3][2] << std::endl;
	std::cout << m[0][3] << " " << m[1][3] << " " << m[2][3] << " " << m[3][3] << std::endl;
}

int main(void)
{
	// Initialise GLFW
	if (!glfwInit())
	{
		std::cerr << "Failed to initialize GLFW." << std::endl;
		return -1;
	}

	glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
	glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
	glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE); // For MacOS
	glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

	// Open a window and create its OpenGL context
	window = glfwCreateWindow(windowWidth, windowHeight, "Anaglyph Rendering", NULL, NULL);
	if (window == NULL)
	{
		std::cerr << "Failed to open a GLFW window." << std::endl;
		glfwTerminate();
		return -1;
	}
	glfwMakeContextCurrent(window);

	// Ensure we can capture the escape key being pressed below
	glfwSetInputMode(window, GLFW_STICKY_KEYS, GL_TRUE);
	glfwSetKeyCallback(window, key_callback);

	// Ensure we can capture mouse cursor movement 
	glfwSetCursorPosCallback(window, cursor_position_callback);

	// Load OpenGL functions, gladLoadGL returns the loaded version, 0 on error.
	int version = gladLoadGL(glfwGetProcAddress);
	if (version == 0)
	{
		std::cerr << "Failed to initialize OpenGL context." << std::endl;
		return -1;
	}

	srand(2024);

	// Background
	glClearColor(163 / 255.0f, 227 / 255.0f, 255 / 255.0f, 1.0f);
	
	glEnable(GL_DEPTH_TEST);
	glEnable(GL_CULL_FACE);

	// Create a box
	Box box;
	box.initialize();

	// Create the scene with a set of boxes represented by their transforms
	generateScene();

	// Set a perspective camera 
	glm::mat4 projectionMatrix = glm::perspective(glm::radians(FoV), (float)windowWidth / windowHeight, zNear, zFar);

	printAnaglyphMode();

	do
	{

		// TODO: Render anaglyph 
		// --------------------------------------------------------------------

		if (anaglyphMode == None) {
			// Clear the screen
			glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
			glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

			// Set camera view matrix 
			glm::mat4 viewMatrix = glm::lookAt(eyeCenter, lookat, up);
			glm::mat4 vp = projectionMatrix * viewMatrix;
			
			// Draw 
			for (int i = 0; i < numBoxes; ++i) {
				box.render(vp, boxTransforms[i]);
			}

		} else {
			
			glm::mat4 vpLeft;
			glm::mat4 vpRight;
			
// Controls:(ik they were already given, but just putting them here for easy reference)
// M            : cycle anaglyph mode
// , / .        : decrease / increase IPD (stereo depth)
// 1 / 0        : show single debug cube / full scene
// Arrow keys   : orbit camera around the scene
// Space        : toggle automatic camera rotation
// R            : reset camera view
// Left mouse   : click and drag to orbit camera
// Esc          : exit


			if (anaglyphMode == ToeIn) {

				// TODO: Implement the toe-in projection here

				//eyes shifted left/right, both look at the same point (lookat/origin).
				glm::vec3 forward = glm::normalize(lookat - eyeCenter);
				glm::vec3 right = glm::normalize(glm::cross(forward, up));
				//Shifting along the camera's right direction(not origianl world X).
				glm::vec3 eyeLeft = eyeCenter - right * (ipd * 0.5f);
				glm::vec3 eyeRight = eyeCenter + right * (ipd * 0.5f);

				glm::mat4 viewLeft = glm::lookAt(eyeLeft,  lookat, up);
				glm::mat4 viewRight = glm::lookAt(eyeRight, lookat, up);
				//Same projection for both eyes
				vpLeft  = projectionMatrix * viewLeft;
                vpRight = projectionMatrix * viewRight;
				
				// ------------------------------------------------------------


			} else if (anaglyphMode == Asymmetric) {	

				// TODO: Implement the asymmetric view frustum here

				//Off-axis stereo: eyes are shifted left/right, BUT view directions stay parallel.
                //We shift the frustum so the virtual screen plane at the world origin converges.
                glm::vec3 forward = glm::normalize(lookat - eyeCenter);
                glm::vec3 right = glm::normalize(glm::cross(forward, up));

                glm::vec3 eyeLeft = eyeCenter - right * (ipd * 0.5f);
                glm::vec3 eyeRight = eyeCenter + right * (ipd * 0.5f);

                //parallel cameras:looking "forward" from each eye,and not at the lookat point.
                glm::mat4 viewLeft = glm::lookAt(eyeLeft,  eyeLeft  + forward, up);
                glm::mat4 viewRight = glm::lookAt(eyeRight, eyeRight + forward, up);

               //off-axis frustums
               float n = zNear;
               float f = zFar;
               float aspect = (float)windowWidth / (float)windowHeight;
               float fovRad = glm::radians(FoV);

               float top = n * tanf(fovRad * 0.5f);
               float bottom = -top;
               float r = top * aspect;
               float l = -r;

               //Convergence distance:distance from center eye to the screen plane at the origin.
               //Guarding against divide-by-zero just in case :) .
               float convergence = glm::length(lookat - eyeCenter);
               if (convergence < 1e-4f) convergence = 1e-4f;

               //Frustum shift (standard off-axis stereo)
               float shift = (ipd * 0.5f) * n / convergence;

               //Left eye frustum is shifted right; right eye frustum shifted left
               glm::mat4 projLeft = glm::frustum(l + shift, r + shift, bottom, top, n, f);
               glm::mat4 projRight = glm::frustum(l - shift, r - shift, bottom, top, n, f);

               vpLeft = projLeft  * viewLeft;
               vpRight = projRight * viewRight;

				// ------------------------------------------------------------

			}

			  // TODO: Implement two-pass rendering to draw the anaglyph
			  //Two-pass anaglyph rendering:
              //once with full mask, then rendering left(red) and right(cyan) with depth cleared between passes.
              glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
              glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

              //Left eye->red only
              glColorMask(GL_TRUE, GL_FALSE, GL_FALSE, GL_TRUE);
              glClear(GL_DEPTH_BUFFER_BIT);
              for (int i = 0; i < numBoxes; ++i) {
	          box.render(vpLeft,boxTransforms[i]);
            }

             //Right eye->cyan(green + blue)
             glColorMask(GL_FALSE, GL_TRUE, GL_TRUE, GL_TRUE);
             glClear(GL_DEPTH_BUFFER_BIT);
             for (int i = 0; i < numBoxes; ++i) {
	           box.render(vpRight,boxTransforms[i]);
            }

             //Restore
             glColorMask(GL_TRUE,GL_TRUE, GL_TRUE, GL_TRUE);

			// ----------------------------------------------------------------
			
		}

		// --------------------------------------------------------------------


		// Animation
		static double lastTime = glfwGetTime();
		double currentTime = glfwGetTime();
		float deltaTime = float(currentTime - lastTime);
		lastTime = currentTime;
		if (rotating) {
         viewAzimuth += 1.0f * deltaTime;
         updateEyeCenterFromAngles();
         } 

		// Swap buffers
		glfwSwapBuffers(window);
		glfwPollEvents();

	} // Check if the ESC key was pressed or the window was closed
	while (!glfwWindowShouldClose(window));

	// Clean up
	box.cleanup();

	// Close OpenGL window and terminate GLFW
	glfwTerminate();

	return 0;
}

// Is called whenever a key is pressed/released via GLFW
void key_callback(GLFWwindow *window, int key, int scancode, int action, int mode)
{
	if (key == GLFW_KEY_SPACE && action == GLFW_PRESS)
	{
		std::cout << "Space key is pressed." << std::endl;
		rotating = !rotating;
	}

	if (key == GLFW_KEY_R && action == GLFW_PRESS)
	{
		std::cout << "Reset." << std::endl;
		rotating = false;
		eyeCenter = originalEyeCenter;
		viewAzimuth = M_PI / 2;
		viewPolar = M_PI / 2;
	}

	if (key == GLFW_KEY_UP && (action == GLFW_REPEAT || action == GLFW_PRESS))
	{
		viewPolar -= 0.1f;
		updateEyeCenterFromAngles();
	}

	if (key == GLFW_KEY_DOWN && (action == GLFW_REPEAT || action == GLFW_PRESS))
	{
		viewPolar += 0.1f;
		updateEyeCenterFromAngles();
	}

	if (key == GLFW_KEY_LEFT && (action == GLFW_REPEAT || action == GLFW_PRESS))
	{
		viewAzimuth -= 0.1f;
		updateEyeCenterFromAngles();
	}

	if (key == GLFW_KEY_RIGHT && (action == GLFW_REPEAT || action == GLFW_PRESS))
	{
		viewAzimuth += 0.1f;
	    updateEyeCenterFromAngles();
	}

	if (key == GLFW_KEY_M && action == GLFW_PRESS) {
        nextAnaglyphMode(); 
		printAnaglyphMode();
	}

	// Adjust the IPD value to match your actual viewing distance
	// Special case: IPD == 0 means no 3D effect.

	if (key == GLFW_KEY_COMMA) {
		ipd -= 0.1f;
		ipd = std::max(ipd, 0.0f);
		std::cout << "IPD: " << ipd << std::endl;
	}

	if (key == GLFW_KEY_PERIOD) {
		ipd += 0.1f;
		std::cout << "IPD: " << ipd << std::endl;
	}

	if (key == GLFW_KEY_1) {
		numBoxes = 1;
		generateScene();
	}

	if (key == GLFW_KEY_0) {
		numBoxes = 100;
		generateScene();
	}

	if (key == GLFW_KEY_ESCAPE && action == GLFW_PRESS)
		glfwSetWindowShouldClose(window, GL_TRUE);
	
	if (key == GLFW_KEY_P && action == GLFW_PRESS) {
	usePart4Scene = !usePart4Scene;
	std::cout << "Part 4 scene: " << (usePart4Scene ? "ON" : "OFF") << std::endl;
	generateScene();
}

}

void cursor_position_callback(GLFWwindow* window, double xpos, double ypos) {
	if (glfwGetMouseButton(window, GLFW_MOUSE_BUTTON_LEFT) != GLFW_PRESS) {
		mouseDragging = false;
		return;
	}
	if (!mouseDragging) {
		mouseDragging = true;
		lastMouseX = xpos;
		lastMouseY = ypos;
		return;
	}
	double dx =xpos - lastMouseX;
	double dy =ypos - lastMouseY;
	lastMouseX =xpos;
	lastMouseY =ypos;

	rotating = false;

	viewAzimuth +=(float)(dx * 0.005);
	viewPolar   +=(float)(dy * 0.005);

	// Clamp to avoid flipping
	const float eps = 0.05f;
	viewPolar = std::max(eps,std::min((float)M_PI - eps, viewPolar));

	updateEyeCenterFromAngles();

}
