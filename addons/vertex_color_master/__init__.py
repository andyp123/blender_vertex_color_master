#  ***** GPL LICENSE BLOCK *****
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#  All rights reserved.
#  ***** GPL LICENSE BLOCK *****

# <pep8 compliant>

# reload submodules if the addon is reloaded 
if "bpy" in locals():
    import importlib
    importlib.reload(vcm_globals)
    importlib.reload(vcm_helpers)
    importlib.reload(vcm_main)
    importlib.reload(vcm_menus)
    importlib.reload(vcm_ops)

import bpy
from . import vcm_main
from . import vcm_menus
from . import vcm_ops
# not used in this file
from . import vcm_globals
from . import vcm_helpers

bl_info = {
    "name": "Vertex Color Master",
    "author": "Andrew Palmer (with contributions from Bartosz Styperek)",
    "version": (0, 9, 0),
    "blender": (3, 6, 0),
    "location": "Vertex Paint | View3D > VCM",
    "description": "Tools for manipulating vertex color data.",
    "warning": "",
    "doc_url": "https://github.com/andyp123/blender_vertex_color_master",
    "tracker_url": "https://github.com/andyp123/blender_vertex_color_master/issues",
    "category": "Paint",
}

classes = (
    vcm_main.VertexColorMasterProperties,
    vcm_ops.VERTEXCOLORMASTER_OT_QuickFill,
    vcm_ops.VERTEXCOLORMASTER_OT_Fill,
    vcm_ops.VERTEXCOLORMASTER_OT_Invert,
    vcm_ops.VERTEXCOLORMASTER_OT_Posterize,
    vcm_ops.VERTEXCOLORMASTER_OT_Remap,
    vcm_ops.VERTEXCOLORMASTER_OT_CopyChannel,
    vcm_ops.VERTEXCOLORMASTER_OT_RgbToGrayscale,
    vcm_ops.VERTEXCOLORMASTER_OT_BlendChannels,
    vcm_ops.VERTEXCOLORMASTER_OT_EditBrushSettings,
    vcm_ops.VERTEXCOLORMASTER_OT_WeightsToColor,
    vcm_ops.VERTEXCOLORMASTER_OT_ColorToWeights,
    vcm_ops.VERTEXCOLORMASTER_OT_UVsToColor,
    vcm_ops.VERTEXCOLORMASTER_OT_ColorToUVs,
    vcm_ops.VERTEXCOLORMASTER_OT_NormalsToColor,
    vcm_ops.VERTEXCOLORMASTER_OT_ColorToNormals,
    vcm_ops.VERTEXCOLORMASTER_OT_IsolateChannel,
    vcm_ops.VERTEXCOLORMASTER_OT_ApplyIsolatedChannel,
    vcm_ops.VERTEXCOLORMASTER_OT_RandomizeMeshIslandColors,
    vcm_ops.VERTEXCOLORMASTER_OT_RandomizeMeshIslandColorsPerChannel,
    vcm_ops.VERTEXCOLORMASTER_OT_FlipBrushColors,
    vcm_ops.VERTEXCOLORMASTER_OT_Gradient,
    vcm_ops.VERTEXCOLORMASTER_OT_BlurChannel,
    vcm_menus.VERTEXCOLORMASTER_PT_MainPanel,
    vcm_menus.VERTEXCOLORMASTER_MT_PieMain,
)

# used to unregister bound shortcuts when the addon is disabled / removed
addon_keymaps = []

def register():
    # fix issue with default brush name changing between 2.80 > 2.81
    if bpy.app.version >= (2, 81, 0):
        default_brush_name = 'Add'

    # add operators
    for c in classes:
        bpy.utils.register_class(c)

    # register properties (see also VertexColorMasterProperties class)
    bpy.types.Scene.vertex_color_master_settings = bpy.props.PointerProperty(
        type=vcm_main.VertexColorMasterProperties)

    # register shortcuts
    wm = bpy.context.window_manager
    if wm.keyconfigs.addon:
        km = wm.keyconfigs.addon.keymaps.new(name='Vertex Paint')
        # pie menu
        kmi = km.keymap_items.new('wm.call_menu_pie', 'V', 'PRESS')
        kmi.properties.name = "VERTEXCOLORMASTER_MT_PieMain"
        kmi.active = True
        addon_keymaps.append((km, kmi))
        # override 'x' to use VCM flip brush colors
        kmi = km.keymap_items.new('vertexcolormaster.brush_colors_flip', 'X', 'PRESS')
        kmi.active = True
        addon_keymaps.append((km, kmi))

def unregister():
    # remove operators
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

    # unregister properties
    del bpy.types.Scene.vertex_color_master_settings

    # unregister shortcuts
    wm = bpy.context.window_manager
    if wm.keyconfigs.addon:
        for km, kmi in addon_keymaps:
            km.keymap_items.remove(kmi)
        addon_keymaps.clear()

# allows running addon from text editor
if __name__ == '__main__':
    register()