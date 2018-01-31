# Vertex Color Master for Blender

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=S3GTZ2J938U6Y&lc=GB&item_name=Andrew%20Palmer&currency_code=GBP&bn=PP%2dDonationsBF%3abtn_donateCC_LG%2egif%3aNonHosted)

An add-on for [Blender](https://www.blender.org/) that adds numerous features to assist working with vertex colors.

![Vertex Color Master UI](https://raw.githubusercontent.com/andyp123/blender_vertex_color_master/master/README_img/vcm_usage_examples.gif)

## Installation
1. Download the script from GitHub by clicking [here](https://github.com/andyp123/blender_vertex_color_master/archive/master.zip).
2. Open the downloaded .zip and extract the file 'vertex_color_master.py' to a temporary place on your computer.
3. In Blender, open the User Preferences (ctrl+alt+p) and switch to the Add-ons tab.
4. Select 'Install Add-on from file...' and select the 'vertex_color_master.py' file you extracted from the .zip.
5. Search for the add-on in the list (enter 'vertex' to quickly find it) and enable it.
6. Save the user settings if you would like the script to always be enabled.

__Note:__ If you are using a 2.79 based Buildbot version of Blender (available [here](https://builder.blender.org/download/)), you may use vertex color alpha, so you will see RGBA channels instead of just RGB as shown in the standard 2.79.0 release of Blender.

## Usage
This add-on is mostly designed for people who use vertex colors as extra non-color data, such as artists making models for games, where such data can be useful for creating interesting shader effects, or for storing baked light data. The tools provided by this add-on allow the user to fill, invert, posterize or remap individual color channels, as well as copy or swap channels between layers and exchange vertex weight and UV data to and from color channels.

The add-on will appear in it's own tab ('Vertex Color Master') in vertex paint mode as shown in the following image.

![Vertex Color Master UI](https://raw.githubusercontent.com/andyp123/blender_vertex_color_master/master/README_img/vertex_color_master.png)


## Brush Settings
Brush settings contains a few of the most useful brush options so that the add-on can be open and useful without needing the full brush menu to be open. This way there is more space in the Tools panel, even on smaller displays.

+ __Match Active Channels__ (on) - With this option enabled, changing the active channels will update the brush color to match the channels that are active, such that enabling only R will give red, R and G will give yellow and all RGB will give white etc. This is useful for painting with add or subtract blend modes. If this is undesirable, disable this option.

### Fill With Color
This will ignore any selected active channels and fill the mesh with the current brush color. It can use the selection mask mode, so this is a handy shortcut for filling selected faces or vertices with a specific color instead of trying to set the value via channels or painting. Note that you can also fill using Blender's built in fill tool (shift + k), which is much faster, but it doesn't support vertex masking, and face masking is handled differently.

+ __Fill Color__ (white) - Color with which to fill the mesh or selection (if using selection mask).


## Active Channels
The active channels section allows the user to enable or disable channels that the functions directly under the active channels will work on. For example, enabling only the R channel will mean that it is the only channel to be affected when the Invert button is pressed, etc. Different combinations of RGBA can be selected by holding the shift key while clicking on the channel buttons.

As channels are activated and deactivated, the brush color will update to match them. If the Add or Subtract brush blending modes are set, this enables the user to paint only on active channels quite easily.

### Isolate Active Channel
When a single channel is selected, the option to isolate it and work in greyscale mode becomes available. Simply press the 'Isolate Active Channel' button and the active channel will be isolated and the Vertex Color Master UI will change to reflect this. Once in isolate channel mode, grayscale should be used instead of color when painting, and some of the usual options will not be visible on the UI. Once changes to the channel have been made, they can be applied by pressing the 'Apply Changes' button, or discarded by pressing 'Discard Changes' instead.

+ __Channel__ (R) - The channel that was isolated can be changed by selecting a different one.

![Isolate Mode](https://raw.githubusercontent.com/andyp123/blender_vertex_color_master/master/README_img/isolate_mode.png)

### Fill / Clear
Fill sets the value of the currently active channel(s) to 1, whereas Clear will set it to 0.

+ __Value__ (1.0) - The value to fill the channel(s) with.

+ __Fill With Color__ (off) - Ignore active channels and fill the vertex color layer with 'Fill Color'.

+ __Fill Color__ (white) - Color to use when 'Fill With Color' is enabled.

### Invert
Inverts the value of the currently active channel(s).

### Posterize
Posterize the value of the currently active channel(s). Useful for cleaning up channels where the value should be 0 or 1, or otherwise snapping the value to increments determined by the number of steps.

+ __Steps__ (2) - The number of value steps to posterize to. For example, setting this to 5 would snap the values of the active channel(s) to 0, 0.25, 0.5, 0.75 and 1, whilst leaving the default setting of 2, would result in black and white.

### Remap
Remap the value of the currently active channel(s). This function takes values in the active channel and scales them based on an input range and output range. It's somewhat similar to using levels in a 2d graphics package, so it can be used to adjust the minimum and maximum brightness, invert etc. If used on individual channels, it can be used to shift colors apart.

+ __Input Range Min__ (0) - Minimum value of the input range.

+ __Input Range Max__ (1) - Maximum value of the input range.

+ __Output Range Min__ (0) - Minimum value of the output range.

+ __Output Range Min__ (1) - Maximum value of the output range.


## Data Transfer
This section allows quick transfer of data between different color layers, vertex groups and uv layers on the same object. Values can be transferred between 'Src' and 'Dst' layers. When using a vertex color layer, the RGBA channel will be selectable from the channel dropdown on the right. If a vertex group is selected (vertex groups are prefixed with 'W:', for weight), the channel dropdown will be disabled. If a UV layer is selected (UVs are prefixed with 'UV:'), channels will not be selectable at all.

Depending on the type of data selected in either 'Src' or 'Dst', a different operations will be available from the UI. If vertex groups or UVs are selected in either 'Src' or 'Dst', a different UI will be shown that enables only simple data transfer. Transfer between two vertex groups, uv layers or vertex groups and uv layer is currently unsupported.

### Copy / Swap
Copy data from the 'Src' layer/channel to the 'Dst' layer/channel. Using swap will swap the data instead of copy.

+ __Swap Channels__ (off) - Swap 'Src' and 'Dst'  channel data instead of just copying from 'Src' to 'Dst'.

+ __All Channels__ (off) - If swap is disabled, the data from the 'Src' channel will be copied to all channels of the 'Dst' layer.

### Blend
Blends the 'Src' channel with the 'Dst' channel and puts the result in the 'Dst' channel by default.

+ __Blend Mode__ (Add) - Set the blending mode to use.

+ __Result Channel__ (R) - Set a different channel to put the resulting data of the blend if overwriting the 'Dst' channel is not desired.

### Src RGB to Luminosity
This calculates the luminosity of the vertex color data in the 'Src' layer and puts the value into each of the RGB channels.

+ __All Channels__ (on) - Copy the luminosity value into each of the RGB channels. If disabled, the luminosity value will only be copied into the 'Dst' layer's selected channel.

### Src to Dst RGB
Copy the value of the 'Src' channel into all channels of the 'Dst' layer.

### Weights to Dst
Copy the weight value of the vertex group in the 'Src' layer to the 'Dst' channel.

### Src to Weights
Copy the value of the 'Src' channel to the vertex group in the 'Dst' layer.

### UVs to Dst
Copy the weight value of the uv layer in the 'Src' layer to the 'Dst' channel.

### Src to UVs
Copy the value of the 'Src' channel to the uv layer in the 'Dst' layer.


## Misc Operations
The 'Misc Operations' section contains features unrelated to the main features of the addon.

### Randomize Mesh Island Colors
All separate parts of a mesh (islands), will be assigned random colors based on various randomization parameters.

+ __Randomize Hue__ (on, 0) - Enable randomization of the hue parameter of generated colors. When disabled, the value to the right will be used instead of being random.

+ __Randomize Saturation__ (off, 1) - Enable randomization of the saturation parameter of generated colors. When disabled, the value to the right will be used instead of being random.

+ __Randomize Value__ (off, 1) - Enable randomization of the value parameter of generated colors. When disabled, the value to the right will be used instead of being random.

+ __Seed__ (1) - The seed determines how the random colors are generated. This ensures the same 'random' colors will be generated each time. To change the colors, change the seed value.

+ __Merge Similar__ (off) - Random colors will be assigned to different mesh islands based on the number of faces of the island. The assigned colors will be random, but if two or more islands have the same face count, they will all share the same color. This is useful for creating an id map from vertex colors.

+ __Order Based__ (off) - Instead of using actual random colors, set the colors based on the number of parts. This will result in the best possible separation of colors, as the default random setting can sometimes give different parts very similar shades.

### Adjust HSV
Enables modification of the Hue, Saturation and Value of vertex color data.

+ __Colorize__ (off) - When enabled, the hue parameter will be set as an absolute value instead of offsetting the existing hue.

+ __Hue__ (0) - Adjust the hue of vertex colors in the mesh.

+ __Saturation__ (0) - Adjust the saturation of vertex colors in the mesh.

+ __Value__ (0) - Adjust the value of vertex colors in the mesh.

### Gradient Tool
When enabled, the gradient tool allows you to draw a line representing the start and end of a gradient in the 3D view. Once the line has been drawn, a gradient will be painted onto the mesh. The brush primary and secondary colors are used to set the gradient colors, but in isolate mode the gradient is always black to white.


## Planned / Possible Features
* Break script into full Add-on.
* Clean up workflow for filling etc.
* Optimisations of channel masked functions.
* Add shortcut to bake AO.
* Add function to bake curvature to colors.
* Add function to set UV islands to random colors.

---

If you like this Add-on and would like to make a donation, you can do so buy clicking this button. Every little helps, even if it just keeps me caffeinated!

[![Donate](https://www.paypalobjects.com/en_US/GB/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=S3GTZ2J938U6Y&lc=GB&item_name=Andrew%20Palmer&currency_code=GBP&bn=PP%2dDonationsBF%3abtn_donateCC_LG%2egif%3aNonHosted)