"""
Embedded icon resources for the BDF Property Updater application.

Contains the application icon as embedded SVG data for standalone deployment.
"""

from PyQt5.QtCore import QByteArray, Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPainter


# Application icon as SVG (embedded for standalone deployment)
APP_ICON_SVG = b'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="256" height="256" viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="docGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#4A90D9;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#2E5C8A;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="meshGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#5CB85C;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#3D8B3D;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="barGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#F0AD4E;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#C87F0A;stop-opacity:1" />
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="2" dy="4" stdDeviation="4" flood-opacity="0.3"/>
    </filter>
    <filter id="glow">
      <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Background circle -->
  <circle cx="128" cy="128" r="120" fill="#1a1a2e" opacity="0.9"/>
  <circle cx="128" cy="128" r="115" fill="none" stroke="#4A90D9" stroke-width="2" opacity="0.5"/>

  <!-- Document base -->
  <path d="M60 40 L170 40 L200 70 L200 216 L60 216 Z"
        fill="url(#docGradient)" filter="url(#shadow)" rx="4"/>

  <!-- Document fold -->
  <path d="M170 40 L170 70 L200 70 Z" fill="#3A7BC8" opacity="0.8"/>

  <!-- Shell mesh pattern (3x3 grid of quads) -->
  <g transform="translate(75, 85)" filter="url(#glow)">
    <rect x="0" y="0" width="35" height="25" fill="url(#meshGradient)" stroke="#2D6A2D" stroke-width="1.5" rx="2"/>
    <rect x="38" y="0" width="35" height="25" fill="url(#meshGradient)" stroke="#2D6A2D" stroke-width="1.5" rx="2"/>
    <rect x="76" y="0" width="35" height="25" fill="url(#meshGradient)" stroke="#2D6A2D" stroke-width="1.5" rx="2"/>
    <rect x="0" y="28" width="35" height="25" fill="url(#meshGradient)" stroke="#2D6A2D" stroke-width="1.5" rx="2"/>
    <rect x="38" y="28" width="35" height="25" fill="url(#meshGradient)" stroke="#2D6A2D" stroke-width="1.5" rx="2"/>
    <rect x="76" y="28" width="35" height="25" fill="url(#meshGradient)" stroke="#2D6A2D" stroke-width="1.5" rx="2"/>
    <text x="55" y="47" font-family="Arial, sans-serif" font-size="11" font-weight="bold" fill="white" text-anchor="middle">t</text>
  </g>

  <!-- Bar elements -->
  <g transform="translate(75, 155)">
    <rect x="0" y="0" width="50" height="18" fill="url(#barGradient)" stroke="#A66A08" stroke-width="1.5" rx="2"/>
    <text x="25" y="13" font-family="Arial, sans-serif" font-size="9" font-weight="bold" fill="white" text-anchor="middle">H&#215;W</text>
    <rect x="58" y="0" width="50" height="18" fill="url(#barGradient)" stroke="#A66A08" stroke-width="1.5" rx="2"/>
  </g>

  <!-- Property update arrow -->
  <g transform="translate(180, 130)">
    <circle cx="0" cy="0" r="22" fill="#E74C3C" filter="url(#shadow)"/>
    <path d="M-8 -3 L4 -3 L4 -8 L12 0 L4 8 L4 3 L-8 3 Z" fill="white"/>
  </g>

  <!-- CSV indicator -->
  <g transform="translate(72, 188)">
    <rect x="0" y="0" width="45" height="16" fill="#34495E" rx="3"/>
    <text x="22" y="12" font-family="Arial, sans-serif" font-size="9" font-weight="bold" fill="#ECF0F1" text-anchor="middle">CSV</text>
  </g>

  <!-- BDF text -->
  <g transform="translate(85, 60)">
    <text font-family="Arial, sans-serif" font-size="22" font-weight="bold" fill="white" opacity="0.9">BDF</text>
  </g>

  <!-- Decorative nodes -->
  <g fill="#5CB85C" filter="url(#glow)">
    <circle cx="75" cy="85" r="3"/>
    <circle cx="110" cy="85" r="3"/>
    <circle cx="148" cy="85" r="3"/>
    <circle cx="186" cy="85" r="3"/>
    <circle cx="75" cy="138" r="3"/>
    <circle cx="186" cy="138" r="3"/>
  </g>
</svg>'''


def get_app_icon() -> QIcon:
    """
    Get the application icon as a QIcon with multiple sizes.

    Returns:
        QIcon with 16x16, 32x32, 48x48, 64x64, 128x128, and 256x256 sizes
    """
    icon = QIcon()

    # Generate icons at multiple sizes for best display
    for size in [16, 24, 32, 48, 64, 128, 256]:
        pixmap = svg_to_pixmap(APP_ICON_SVG, size, size)
        if pixmap:
            icon.addPixmap(pixmap)

    return icon


def svg_to_pixmap(svg_data: bytes, width: int, height: int) -> QPixmap:
    """
    Convert SVG data to a QPixmap of the specified size.

    Args:
        svg_data: SVG content as bytes
        width: Desired width in pixels
        height: Desired height in pixels

    Returns:
        QPixmap rendered from the SVG
    """
    renderer = QSvgRenderer(QByteArray(svg_data))
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.transparent)  # Transparent background

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return pixmap


def get_app_icon_pixmap(size: int = 256) -> QPixmap:
    """
    Get the application icon as a QPixmap of specified size.

    Args:
        size: Size in pixels (width and height)

    Returns:
        QPixmap of the application icon
    """
    return svg_to_pixmap(APP_ICON_SVG, size, size)
