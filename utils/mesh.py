import numpy as np


def calculate_triangle_area(v1, v2, v3):
    a = np.linalg.norm(v2 - v1)
    b = np.linalg.norm(v3 - v2)
    c = np.linalg.norm(v1 - v3)
    s = (a + b + c) / 2  # Semi-perimeter
    area = np.sqrt(s * (s - a) * (s - b) * (s - c))
    return area


def calculate_surface_area(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()

    vertices = []
    faces = []

    for line in lines[2:]:  # Skip the header line
        if line.startswith('3'):  # Face definition
            face = [int(x) for x in line.split()[1:]]
            faces.append(face)
        else:  # Vertex coordinates
            coords = [float(x) for x in line.split()]
            vertices.append(coords)

    total_area = 0
    for face in faces:
        v1 = np.array(vertices[face[0]])
        v2 = np.array(vertices[face[1]])
        v3 = np.array(vertices[face[2]])
        area = calculate_triangle_area(v1, v2, v3)
        total_area += area

    return total_area


if __name__ == "__main__":
    filename = 'm1609.off'
    surface_area = calculate_surface_area(filename)
    print("Surface Area:", surface_area)
