"""
AIDA Radar Chart — Visualización Canvas para Scores AIDA
===========================================================
Dibuja un radar chart (telaraña) con los 4 scores AIDA usando Tkinter Canvas.
"""

import tkinter as tk
import math


def draw_aida_radar(canvas: tk.Canvas, scores: dict, 
                    width: int = 220, height: int = 220,
                    bg_color: str = "#1e1e1e",
                    grid_color: str = "#333333",
                    fill_color: str = "#4CAF50",
                    line_color: str = "#2E7D32") -> None:
    """
    Dibuja un radar chart AIDA en un Canvas de Tkinter.
    
    Args:
        canvas: Tkinter Canvas widget
        scores: Dict con keys 'attention', 'interest', 'decision', 'action' (0-100)
        width, height: Dimensiones del canvas
        bg_color: Color de fondo
        grid_color: Color de la cuadrícula
        fill_color: Color de relleno del polígono
        line_color: Color del borde del polígono
    """
    canvas.delete("all")
    
    cx, cy = width // 2, height // 2
    radius = min(cx, cy) - 20
    
    labels = ["Attention", "Interest", "Decision", "Action"]
    keys = ["attention", "interest", "decision", "action"]
    angles = [0, 90, 180, 270]  # Arriba, derecha, abajo, izquierda
    
    # Dibujar cuadrícula (3 niveles: 25%, 50%, 75%, 100%)
    for level in [0.25, 0.5, 0.75, 1.0]:
        r = radius * level
        points = []
        for angle_deg in angles:
            rad = math.radians(angle_deg - 90)
            x = cx + r * math.cos(rad)
            y = cy + r * math.sin(rad)
            points.append((x, y))
        points.append(points[0])  # Cerrar polígono
        
        # Dibujar cuadrícula
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            canvas.create_line(x1, y1, x2, y2, fill=grid_color, width=1)
    
    # Dibujar líneas de los ejes
    for angle_deg in angles:
        rad = math.radians(angle_deg - 90)
        x = cx + radius * math.cos(rad)
        y = cy + radius * math.sin(rad)
        canvas.create_line(cx, cy, x, y, fill=grid_color, width=1, dash=(2, 4))
    
    # Calcular puntos del score
    score_points = []
    for i, key in enumerate(keys):
        val = min(100, max(0, scores.get(key, 0))) / 100.0
        rad = math.radians(angles[i] - 90)
        x = cx + radius * val * math.cos(rad)
        y = cy + radius * val * math.sin(rad)
        score_points.append((x, y))
    
    # Dibujar polígono de scores
    if score_points:
        flat = []
        for pt in score_points:
            flat.append(pt[0])
            flat.append(pt[1])
        canvas.create_polygon(flat, fill=fill_color, outline=line_color, width=2, stipple="")
    
    # Dibujar puntos en cada vértice
    for x, y in score_points:
        canvas.create_oval(x-4, y-4, x+4, y+4, fill=line_color, outline="")
    
    # Etiquetas
    for i, label in enumerate(labels):
        rad = math.radians(angles[i] - 90)
        label_r = radius + 18
        x = cx + label_r * math.cos(rad)
        y = cy + label_r * math.sin(rad)
        val = scores.get(keys[i], 0)
        canvas.create_text(x, y, text=f"{label}\n{val}%", 
                          fill="#d4d4d4", font=("Segoe UI", 8, "bold"),
                          justify=tk.CENTER)
    
    # Score promedio en el centro
    avg = sum(scores.get(k, 0) for k in keys) / 4
    canvas.create_text(cx, cy, text=f"{avg:.0f}%", 
                      fill="#FFD700", font=("Segoe UI", 14, "bold"))