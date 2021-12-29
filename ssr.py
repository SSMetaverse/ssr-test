"""Simple server side rendering prototype"""

import io
import moderngl
import numpy as np
import pyrr
import fastapi
import PIL.Image

app = fastapi.FastAPI()

# OpenGL context (standalone means we attach a render buffer)
ctx = moderngl.create_context(standalone=True, require=330)

# Minimal shaders
program = ctx.program(
    vertex_shader='''
        #version 330
        uniform mat4 projection;
        uniform mat4 model;
        uniform mat4 view;
        in vec3 in_vert;
        in vec3 in_color;
        out vec3 color;
        void main() {
            gl_Position = projection * view * model * vec4(in_vert, 1.0);
            color = in_color;
        }
    ''',
    fragment_shader='''
        #version 330
        in vec3 color;
        out vec4 fragColor;
        void main() {
            fragColor = vec4(color, 1.0);
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
    vao.render(moderngl.TRIANGLES)

    # Convert into a PNG image format
    image = PIL.Image.new("RGB", fbo.size)
    image.frombytes(fbo.read(), "raw", "RGB", 0, -1)
    data = io.BytesIO()
    image.save(data, format="png")
    data.seek(0)

    # Return the image
    return fastapi.responses.Response(data.read(), media_type="image/png")
