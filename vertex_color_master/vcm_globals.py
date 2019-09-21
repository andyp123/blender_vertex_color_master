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

red_id = 'R'
green_id = 'G'
blue_id = 'B'
alpha_id = 'A'

valid_channel_ids = 'RGBA'

type_vcol = 'VCOL'
type_vgroup = 'VGROUP'
type_uv = 'UV'
type_normal = 'NORMALS'
valid_layer_types = [type_vcol, type_vgroup, type_uv, type_normal]

channel_items = ((red_id, "R", ""),
                 (green_id, "G", ""),
                 (blue_id, "B", ""),
                 (alpha_id, "A", ""))

brush_blend_mode_items = (('MIX', "Mix", ""),
                          ('ADD', "Add", ""),
                          ('SUB', "Sub", ""),
                          ('MUL', "Multiply", ""),
                          ('BLUR', "Blur", ""),
                          ('LIGHTEN', "Lighten", ""),
                          ('DARKEN', "Darken", ""))

channel_blend_mode_items = (('ADD', "Add", ""),
                            ('SUB', "Subtract", ""),
                            ('MUL', "Multiply", ""),
                            ('DIV', "Divide", ""),
                            ('LIGHTEN', "Lighten",  ""),
                            ('DARKEN', "Darken", ""),
                            ('MIX', "Mix", ""))

default_brush_name = 'Draw' # Changed to Add in 2.81 for some reason

 # VCM-ISO_<CHANNEL_ID>_<VCOL_ID> ex. VCM-ISO_R_Col
isolate_mode_name_prefix = 'VCM-ISO'