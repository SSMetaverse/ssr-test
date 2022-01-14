"""Simple server side rendering prototype"""

import io
import moderngl
import numpy as np
import pyrr
import fastapi
import PIL.Image
import pywavefront

from root_path_middleware import RootPathMiddleware

app = fastapi.FastAPI()

# OpenGL context (standalone means we attach a render buffer)
ctx = moderngl.create_context(standalone=True, require=330)

# Minimal shaders (note that in_norm and v_norm get optimized away)
program = ctx.program(
    vertex_shader='''
        #version 330
        uniform mat4 projection;
        uniform mat4 model;
        uniform mat4 view;
        in vec3 in_vert;
        in vec3 in_color;
        in vec3 in_norm;
        in vec2 in_text;
        out vec3 color;
        out vec3 v_norm;
        out vec2 v_text;
        void main() {
            gl_Position = projection * view * model * vec4(in_vert, 1.0);
            color = in_color;
            v_norm = in_norm;
            v_text = in_text;
        }
    ''',
    fragment_shader='''
        #version 330
        uniform sampler2D texture_sampler;
        uniform int isTextured;
        in vec3 color;
        in vec3 v_norm;
        in vec2 v_text;
        out vec4 fragColor;
        void main() {
            if (isTextured > 0) {
                fragColor = texture(texture_sampler, v_text);
            } else {
                fragColor = vec4(color, 1.0);
            };
        }
    ''',
)

# Triangle coordinates and colours
positions = np.array([[-1, -1, 0], [1, -1, 0], [0, 1, 0]], dtype="f4")
colours = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype="f4")

# Format: [x, y, z, r, g, b, ...]
vertices = np.hstack([positions, colours])

# Load into a vertex array
vbo = ctx.buffer(vertices)
vao = ctx.simple_vertex_array(program, vbo, "in_vert", "in_color")

# Load cube.obj
cube = pywavefront.Wavefront("cube.obj")
assert len(cube.materials) == 1
material, = cube.materials.values()
assert material.vertex_format == "T2F_N3F_V3F"
cube_data = np.array(material.vertices, dtype="f4")
cube_data = cube_data.reshape(-1, material.vertex_size)

# Get only the texture and vertex data (ignore the normals)
cube_t = cube_data[:, 0:2]
cube_n = cube_data[:, 2:5]
cube_v = cube_data[:, 5:8]
cube_vertices = np.hstack([cube_t, cube_v])

# Create VBO and VAO
cube_vbo = ctx.buffer(cube_vertices)
cube_vao = ctx.simple_vertex_array(program, cube_vbo, "in_text", "in_vert")

# Load grassblock.png (flip vertically because OpenGL has 0,0 at bottom left)
cube_image = PIL.Image.open("grassblock.png")
cube_image = cube_image.transpose(PIL.Image.FLIP_TOP_BOTTOM)
cube_texture = ctx.texture(cube_image.size, 4, cube_image.tobytes())
cube_texture.filter = moderngl.NEAREST, moderngl.NEAREST

# Enable depth testing (so the cube doesnt get rendered on top of the triangle)
ctx.enable(moderngl.DEPTH_TEST)

# Server endpoint that returns a PNG image
@app.get(
    "/render",
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "Rendered image",
        }
    },
)
async def render(
    # Position
    x: float = 0, y: float = 0, z: float = 0,
    # Camera
    rx: float = 0, ry: float = 0, rz: float = 0,
    # Output
    width: int = 800, height: int = 600,
):

    assert width in range(1, 4097)
    assert height in range(1, 4097)

    # Create a buffer to render to
    fbo = ctx.simple_framebuffer((width, height))
    fbo.use()
    fbo.clear(0, 0, 0, 1)

    # Update uniforms
    program["model"].write(
        pyrr.matrix44.create_from_translation([0, 0, -1], dtype="f4")
    )
    program["view"].write(
        pyrr.matrix44.create_from_translation([-x, -y, -z], dtype="f4")
        @ pyrr.matrix44.create_from_eulers([rx, ry, rz], dtype="f4")
    )
    program["projection"].write(
        pyrr.matrix44.create_perspective_projection_matrix(
            80, width / height, 0.01, 50, dtype="f4",
        )
    )

    # Render the triangle
    program["isTextured"] = 0
    vao.render(moderngl.TRIANGLES)

    # Render the cube
    program["model"].write(
        pyrr.matrix44.create_from_translation([0, 0, -3], dtype="f4")
    )
    program["isTextured"] = 1
    cube_texture.use()
    cube_vao.render(moderngl.TRIANGLES)

    # Convert into a PNG image format
    image = PIL.Image.new("RGB", fbo.size)
    image.frombytes(fbo.read(), "raw", "RGB", 0, -1)
    data = io.BytesIO()
    image.save(data, format="png")
    data.seek(0)

    # Return the image
    return fastapi.responses.Response(data.read(), media_type="image/png")

@app.get("/", response_class=fastapi.responses.HTMLResponse)
async def root():
    return '''<p>go check out <a href="docs">docs</a> or something</p>'''

# Middleware to make docs work when there's a reverse proxy
app.add_middleware(RootPathMiddleware)
