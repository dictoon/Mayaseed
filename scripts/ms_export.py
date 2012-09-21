
#
# Copyright (c) 2012 Jonathan Topf
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#


import maya.cmds as cmds
import maya.mel as mel 
import maya.utils as mu
import os
import time
import re
import subprocess
import sys
import ms_commands
import ms_export_obj
import time

inch_to_meter = 0.02539999983236


#--------------------------------------------------------------------------------------------------
# WriteXml class.
#--------------------------------------------------------------------------------------------------

class WriteXml():
    spaces_per_indentation_level = 4

    def __init__(self, file_path):
        self.indentation_level = 0
        self.file_object = None
        try:
            self.file_object = open(file_path, 'w')
        except IOError:
            error_msg = 'IO error: failed to open {0} for writing.'.format(file_path)
            cmds.error(error_msg)
            raise RuntimeError(error_msg)

    def startElement(self,str):
        self.file_object.write(((self.indentation_level * self.spaces_per_indentation_level) * ' ') + "<" + str + '>\n')
        self.indentation_level += 1
        
    def endElement(self, str):
        self.indentation_level -= 1
        self.file_object.write(((self.indentation_level * self.spaces_per_indentation_level) * ' ') + '</' + str + '>\n')
        
    def appendElement(self, str):
        self.file_object.write(((self.indentation_level * self.spaces_per_indentation_level) * ' ') + '<' + str + '/>\n')

    def appendParameter(self, name, value):
        self.file_object.write(((self.indentation_level * self.spaces_per_indentation_level) * ' ') + '<parameter name="{0}" value="{1}" />\n'.format(name, value))

    def appendLine(self, str):
        self.file_object.write(((self.indentation_level * self.spaces_per_indentation_level) * ' ') + str + '\n')

    def close(self):
        self.file_object.close() #close file


#--------------------------------------------------------------------------------------------------
# cancelExport function.
#--------------------------------------------------------------------------------------------------

def checkExportCancelled():
    if cmds.progressWindow(query=True, isCancelled=True):
        cmds.progressWindow(endProgress=1)
        raise RuntimeError('Export Cancelled')

#--------------------------------------------------------------------------------------------------
# writeTransform function.
#--------------------------------------------------------------------------------------------------

def writeTransform(doc, scale = 1, object=False, motion=False, motion_samples=2):
    if motion:
        start_time = cmds.currentTime(query=True)

        if motion_samples < 2:
            print('Motion samples is set too low, must be atleast 2, using 2')
            motion_samples = 2
        sample_interval = 1.0/(motion_samples - 1)

        cmds.select(object)
        cmds.currentTime(cmds.currentTime(query=True)-1)

        for i in range(motion_samples):
            new_time = start_time + (sample_interval * i)
            cmds.currentTime(new_time)
            cmds.refresh()

            if (object):
                m = cmds.xform(object, query=True, ws=True, matrix=True)
                transform = [m[0],m[1],m[2],m[3]], [m[4],m[5],m[6],m[7]], [m[8],m[9],m[10],m[11]], [m[12],m[13],m[14],m[15]]
            else:
                transform = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]

            doc.startElement('transform time="{0:03}"'.format(i))
            doc.appendElement('scaling value="{0}"'.format(scale))
            doc.startElement('matrix')

            doc.appendLine('{0:.15f} {1:.15f} {2:.15f} {3:.15f}'.format(transform[0][0], transform[1][0], transform[2][0], transform[3][0]))
            doc.appendLine('{0:.15f} {1:.15f} {2:.15f} {3:.15f}'.format(transform[0][1], transform[1][1], transform[2][1], transform[3][1]))
            doc.appendLine('{0:.15f} {1:.15f} {2:.15f} {3:.15f}'.format(transform[0][2], transform[1][2], transform[2][2], transform[3][2]))
            doc.appendLine('{0:.15f} {1:.15f} {2:.15f} {3:.15f}'.format(transform[0][3], transform[1][3], transform[2][3], transform[3][3]))    

            doc.endElement('matrix')
            doc.endElement('transform')

        cmds.currentTime(start_time)
        cmds.select(cl=True)

    else:

        transform = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
        if (object):
            m = cmds.xform(object, query=True, ws=True, matrix=True)
            transform = [m[0],m[1],m[2],m[3]], [m[4],m[5],m[6],m[7]], [m[8],m[9],m[10],m[11]], [m[12],m[13],m[14],m[15]]

        doc.startElement('transform')
        doc.appendElement('scaling value="{0}"'.format(scale))
        doc.startElement('matrix')

        doc.appendLine('{0:.15f} {1:.15f} {2:.15f} {3:.15f}'.format(transform[0][0], transform[1][0], transform[2][0], transform[3][0]))
        doc.appendLine('{0:.15f} {1:.15f} {2:.15f} {3:.15f}'.format(transform[0][1], transform[1][1], transform[2][1], transform[3][1]))
        doc.appendLine('{0:.15f} {1:.15f} {2:.15f} {3:.15f}'.format(transform[0][2], transform[1][2], transform[2][2], transform[3][2]))
        doc.appendLine('{0:.15f} {1:.15f} {2:.15f} {3:.15f}'.format(transform[0][3], transform[1][3], transform[2][3], transform[3][3]))    

        doc.endElement('matrix')
        doc.endElement('transform')


#--------------------------------------------------------------------------------------------------
# getMayaParams function.
#--------------------------------------------------------------------------------------------------

def getMayaParams(render_settings_node):
    print('getting params from ui')

    params = {'error':False}

    params['entityDefs'] = ms_commands.getEntityDefs(os.path.join(ms_commands.ROOT_DIRECTORY, 'scripts', 'appleseedEntityDefs.xml'))

    #main settings
    params['outputDir'] = cmds.getAttr(render_settings_node + '.output_directory')
    params['fileName'] = cmds.getAttr(render_settings_node + '.output_file')
    params['convertShadingNodes'] = cmds.getAttr(render_settings_node + '.convert_shading_nodes_to_textures')
    params['convertTexturesToExr'] = cmds.getAttr(render_settings_node + '.convert_textures_to_exr')
    params['overwriteExistingExrs'] = cmds.getAttr(render_settings_node + '.overwrite_existing_textures')
    params['fileName'] = cmds.getAttr(render_settings_node + '.output_file')
    params['exportCameraBlur'] = cmds.getAttr(render_settings_node + '.export_camera_blur')
    params['exportTransformationBlur'] = cmds.getAttr(render_settings_node + '.export_transformation_blur')
    params['exportDeformationBlur'] = cmds.getAttr(render_settings_node + '.export_deformation_blur')
    params['motionSamples'] = cmds.getAttr(render_settings_node + '.motion_samples')
    params['exportAnimation'] = cmds.getAttr(render_settings_node + '.export_animation')
    params['animationStartFrame'] = cmds.getAttr(render_settings_node + '.animation_start_frame')
    params['animationEndFrame'] = cmds.getAttr(render_settings_node + '.animation_end_frame')
    params['animatedTextures'] = cmds.getAttr(render_settings_node + '.export_animated_textures')
    params['scene_scale'] = 1
    
    #Advanced options
    #scene
    if cmds.listConnections(render_settings_node + '.environment'):
        params['environment'] = cmds.listRelatives(cmds.listConnections(render_settings_node + '.environment')[0])[0]
    else:
        params['environment'] = False

    #cameras
    # params['sceneCameraExportAllCameras'] = cmds.checkBox('ms_sceneCameraExportAllCameras', query=True, value=True)
    params['sceneCameraDefaultThinLens'] = cmds.getAttr(render_settings_node + '.export_all_cameras_as_thinlens')
    
    #assemblies
    #materials
    params['matLambertBSDF'] = 'Lambertian'
    params['matLambertEDF'] = 'None'
    params['matLambertSurfaceShader'] = 'Physical'
    params['matBlinnBSDF'] = 'Ashikhmin-Shirley'
    params['matBlinnEDF'] = 'None'
    params['matBlinnSurfaceShader'] = 'Physical'
    params['matPhongBSDF'] = 'Ashikhmin-Shirley'
    params['matPhongEDF'] = 'None'
    params['matPhongSurfaceShader'] = 'Physical'
    params['matSurfaceShaderBSDF'] = 'Lambertian'
    params['matSurfaceShaderEDF'] = 'Diffuse'
    params['matSurfaceShaderSurfaceShader'] = 'Physical'
    params['matDefaultBSDF'] = 'Lambertian'
    params['matDefaultEDF'] = 'None'
    params['matDefaultSurfaceShader'] = 'Physical'
    params['matDoubleShade'] = cmds.getAttr(render_settings_node + '.double_sided_shading')

    # output 
    if cmds.listConnections(render_settings_node + '.camera'):
        params['outputCamera'] = cmds.listConnections(render_settings_node + '.camera')[0]
    else:
        cmds.warning('no camera connected to',  render_settings_node, 'using persp')
        params['outputCamera'] = 'persp'
    
    if cmds.getAttr(render_settings_node + '.color_space') == 1:
        params['outputColorSpace'] = 'linear_rgb'
    elif cmds.getAttr(render_settings_node + '.color_space') == 2:
        params['outputColorSpace'] = 'spectral'
    elif cmds.getAttr(render_settings_node + '.color_space') == 3:
        params['outputColorSpace'] = 'ciexyz'
    else:
        params['outputColorSpace'] = 'srgb'

    params['outputResWidth'] = cmds.getAttr(render_settings_node + '.width')
    params['outputResHeight'] = cmds.getAttr(render_settings_node + '.height')

    # configuration
    # custom Final config
    params['customFinalConfigCheck'] = cmds.getAttr(render_settings_node + '.export_custom_final_config')
    params['customFinalConfigEngine'] = cmds.getAttr(render_settings_node + '.final_lighting_engine')

    params['customFinalConfigMinSamples'] = cmds.getAttr(render_settings_node + '.min_samples')
    params['customFinalConfigMaxSamples'] = cmds.getAttr(render_settings_node + '.max_samples')


    params['drtDLBSDFSamples'] = cmds.getAttr(render_settings_node + '.drt_dl_bsdf_samples')
    params['drtDLLightSamples'] = cmds.getAttr(render_settings_node + '.drt_dl_light_samples')
    params['drtEnableIBL'] = cmds.getAttr(render_settings_node + '.drt_enable_ibl')
    params['drtIBLBSDFSamples'] = cmds.getAttr(render_settings_node + '.drt_ibl_bsdf_samples')
    params['drtIBLEnvSamples'] = cmds.getAttr(render_settings_node + '.drt_ibl_env_samples')
    params['drtMaxPathLength'] = cmds.getAttr(render_settings_node + '.drt_max_path_length')
    params['drtRRMinPathLength'] = cmds.getAttr(render_settings_node + '.drt_rr_min_path_length')

    params['ptDLLightSamples'] = cmds.getAttr(render_settings_node + '.pt_dl_light_samples')
    params['ptEnableCaustics'] = cmds.getAttr(render_settings_node + '.pt_enable_caustics')
    params['ptEnableDL'] = cmds.getAttr(render_settings_node + '.pt_enable_dl')
    params['ptEnableIBL'] = cmds.getAttr(render_settings_node + '.pt_enable_ibl')
    params['ptIBLBSDFSamples'] = cmds.getAttr(render_settings_node + '.pt_ibl_bsdf_samples')
    params['ptIBLEnvSamples'] = cmds.getAttr(render_settings_node + '.pt_ibl_env_samples')
    params['ptMaxPathLength'] = cmds.getAttr(render_settings_node + '.pt_max_path_length')
    params['ptNextEventEstimation'] = cmds.getAttr(render_settings_node + '.pt_next_event_estimation')
    params['ptRRMinPathLength'] = cmds.getAttr(render_settings_node + '.pt_rr_min_path_length')

    params['gtrFilterSize'] = cmds.getAttr(render_settings_node + '.gtr_filter_size')
    params['gtrMinSamples'] = cmds.getAttr(render_settings_node + '.gtr_min_samples')
    params['gtrMaxSamples'] = cmds.getAttr(render_settings_node + '.gtr_max_samples')
    params['gtrMaxContrast'] = cmds.getAttr(render_settings_node + '.gtr_max_contrast')
    params['gtrMaxVariation'] = cmds.getAttr(render_settings_node + '.gtr_max_variation')

    if cmds.getAttr(render_settings_node + '.gtr_sampler') == 0:
        params['gtrSampler'] = 'uniform'
    else:
        params['gtrSampler'] = 'adaptive'

    # select obj exporter
    if cmds.pluginInfo(('ms_export_obj_' + str(int(mel.eval('getApplicationVersionAsFloat()')))), query=True, r=True):
        params['obj_exporter'] = ms_commands.export_obj
    else:
        cmds.warning('no compiled obj exporter present, exporting using python obj exporter')
        params['obj_exporter'] = ms_export_obj.export


    return params


#--------------------------------------------------------------------------------------------------
# Color class.
#--------------------------------------------------------------------------------------------------

class Color():
    def __init__(self, name, color, multiplier):
        self.name = name
        self.color = color
        self.multiplier = multiplier
        self.color_space = 'srgb'
        self.wavelength_range = '400.0 700.0'
        self.alpha = 1.0

    def writeXML(self, doc):
        print('writing color {0}'.format(self.name))
        doc.startElement('color name="{0}"'.format(self.name))       
        doc.appendParameter('color', '{0:.6f} {1:.6f} {2:.6f}'.format(self.color[0], self.color[1], self.color[2]))
        doc.appendParameter('color_space', self.color_space)
        doc.appendParameter('multiplier', self.multiplier)
        doc.appendParameter('alpha', self.alpha)

        doc.startElement('values')
        doc.appendLine('{0:.6f} {1:.6f} {2:.6f}'.format(self.color[0], self.color[1], self.color[2]))
        doc.endElement('values')
        doc.startElement('alpha')
        doc.appendLine('{0:.6f}'.format(self.alpha))
        doc.endElement('alpha')
        doc.endElement('color')


#--------------------------------------------------------------------------------------------------
# Texture class.
#--------------------------------------------------------------------------------------------------

class Texture():
    def __init__(self, name, file_name, color_space='srgb', alpha_as_luminance=False):
        self.name = name

        directory = ms_commands.legalizeName(os.path.split(file_name)[0])
        filename = ms_commands.legalizeName(os.path.split(file_name)[1])
        self.filepath = os.path.join(directory, filename)

        self.color_space = color_space

        if alpha_as_luminance:
            self.alpha_mode = 'luminance'
        else:
            self.alpha_mode = 'alpha_channel'

    def writeXMLObject(self, doc):
        print('writing texture object {0}'.format(self.name))
        doc.startElement('texture name="{0}" model="disk_texture_2d"'.format(self.name))
        doc.appendParameter('color_space', self.color_space)
        doc.appendParameter('filename', self.filepath)
        doc.endElement('texture')

    def writeXMLInstance(self, doc):
        print('writing texture instance {0}_inst'.format(self.name))
        doc.startElement('texture_instance name="{0}_inst" texture="{0}"'.format(self.name, self.name))
        doc.appendParameter('addressing_mode', 'clamp')
        doc.appendParameter('filtering_mode', 'bilinear')
        doc.appendParameter('alpha_mode', self.alpha_mode)
        doc.endElement('texture_instance')


#--------------------------------------------------------------------------------------------------
# Light class.
#--------------------------------------------------------------------------------------------------

class Light():
    def __init__(self, params, name, model='point_light'):
        self.params = params
        self.name = name
        self.model = model
        self.color_name = self.name + '_exitance'
        self.color = cmds.getAttr(self.name+'.color')[0]
        self.multiplier = cmds.getAttr(self.name+'.intensity')
        self.decay = cmds.getAttr(self.name+'.decayRate')
        self.inner_angle = None
        self.outer_angle = None

    def writeXML(self, doc):
        print('writing light: {0}'.format(self.name))
        doc.startElement('light name="{0}" model="{1}"'.format(self.name, self.model))

        # add spot light attribs if they exist
        if self.model == 'spot_light':
            doc.appendParameter('inner_angle', self.inner_angle)
            doc.appendParameter('outer_angle', self.outer_angle)

        doc.appendParameter('exitance', self.color_name)

        writeTransform(doc, self.params['scene_scale'], self.name, self.params['exportTransformationBlur'], self.params['motionSamples'])
        doc.endElement('light')


#--------------------------------------------------------------------------------------------------
# Material class.
#--------------------------------------------------------------------------------------------------

class Material():
    def __init__(self, params, maya_node):
        self.params = params
        self.name = maya_node
        self.safe_name = ms_commands.legalizeName(self.name)
        self.duplicate_shaders = cmds.getAttr(self.name + '.duplcated_front_attributes_on_back')
        self.shading_nodes = []
        self.colors = []
        self.textures = []

        self.bsdf_front = self.getMayaAttr(self.name + '.BSDF_front_color')
        self.edf_front = self.getMayaAttr(self.name + '.EDF_front_color')
        self.surface_shader_front = self.getMayaAttr(self.name + '.surface_shader_front_color')
        self.normal_map_front = self.getMayaAttr(self.name + '.normal_map_front_color')
        self.alpha_map = self.getMayaAttr(self.name + '.alpha_map_color')
        if self.alpha_map != None:
            self.alpha_map.alpha_mode = 'luminance'

        #only use front shaders on back if box is checked
        if not self.duplicate_shaders:
            self.bsdf_back = self.getMayaAttr(self.name + '.BSDF_back_color')
            self.edf_back = self.getMayaAttr(self.name + '.EDF_back_color')
            self.surface_shader_back = self.getMayaAttr(self.name + '.surface_shader_back_color')
            self.normal_map_back = self.getMayaAttr(self.name + '.normal_map_back_color')

            self.shader_connections = [self.bsdf_front,
                                  self.bsdf_back,
                                  self.edf_front,
                                  self.edf_back,
                                  self.surface_shader_front,
                                  self.surface_shader_back]

            self.texture_connections = [self.normal_map_front,
                                   self.normal_map_back,
                                   self.alpha_map]

        else: 
            self.bsdf_back, self.edf_back, self.surface_shader_back, self.normal_map_back = self.bsdf_front, self.edf_front, self.surface_shader_front, self.normal_map_front

            self.shader_connections = [self.bsdf_front,
                                       self.edf_front,
                                       self.surface_shader_front]

            self.texture_connections = [self.normal_map_front,
                                        self.alpha_map]

    def getMayaAttr(self, attr_name):
        connection = cmds.listConnections(attr_name)
        if connection:
            if cmds.nodeType(connection[0]) == 'ms_appleseed_shading_node':
                shading_node = ShadingNode(self.params, connection[0])
                self.shading_nodes = self.shading_nodes + [shading_node] + shading_node.getChildren()
                self.colors = self.colors + shading_node.colors
                return shading_node

            elif cmds.nodeType(connection[0]) == 'file':
                maya_texture_file = ms_commands.getFileTextureName(connection[0])
                texture = ms_commands.convertTexToExr(maya_texture_file, params['absolute_tex_dir'], overwrite=self.params['overwriteExistingExrs'], pass_through=False)
                texture_node = Texture(self.params, connection[0], os.path.join(params['tex_dir'], os.path.split(texture)[1]))
                self.texture_nodes = self.texture_nodes + [texture_node]
                return texture_node

        else:
            return None

    def getShadingNodes(self):
        return self.shading_nodes

    def writeXML(self, doc):
        print 'diplicate shader =', self.duplicate_shaders
        if self.duplicate_shaders:
            print('writing material {0}'.format(self.name))
            doc.startElement('material name="{0}" model="generic_material"'.format(self.name))
            if self.bsdf_front:
                doc.appendParameter('bsdf', self.bsdf_front.name)
            if self.edf_front:
                doc.appendParameter('edf', self.edf_front.name)
            if self.surface_shader_front:
                doc.appendParameter('surface_shader', self.surface_shader_front.name)
            if self.alpha_map:
                doc.appendParameter('alpha_map', self.alpha_map_front.name)
            if self.normal_map_front:
                doc.appendParameter('normal_map', self.normal_map_front.name)
            doc.endElement('material')
        else:
            print('writing material {0}_front'.format(self.name))
            doc.startElement('material name="{0}_front" model="generic_material"'.format(self.name))
            if self.bsdf_front:
                doc.appendParameter('bsdf', self.bsdf_front.name)
            if self.edf_front:
                doc.appendParameter('edf', self.edf_front.name)
            if self.surface_shader_front:
                doc.appendParameter('surface_shader', self.surface_shader_front.name)
            if self.alpha_map:
                doc.appendParameter('alpha_map', self.alpha_map_front.name)
            if self.normal_map_front:
                doc.appendParameter('normal_map', self.normal_map_front.name)
            doc.endElement('material')    

            print('writing material {0}_back'.format(self.name))
            doc.startElement('material name="{0}_back" model="generic_material"'.format(self.name))
            if self.bsdf_back:
                doc.appendParameter('bsdf', self.bsdf_back.name)
            if self.edf_back:
                doc.appendParameter('edf', self.edf_back.name)
            if self.surface_shader_back:
                doc.appendParameter('surface_shader', self.surface_shader_back.name)
            if self.alpha_map:
                doc.appendParameter('alpha_map', self.alpha_map_back.name)
            if self.normal_map_back:
                doc.appendParameter('normal_map', self.normal_map_back.name)
            doc.endElement('material') 

#--------------------------------------------------------------------------------------------------
# ShadingNode class.
#--------------------------------------------------------------------------------------------------

class ShadingNode():
    def __init__(self, params, name, attributes=False, node_type=False, model=False):
        self.params = params
        self.name = name                
        self.type = node_type           # bsdf etc
        self.model = model              # ashikhmin-shirley etc
        self.child_shading_nodes = []
        self.attributes = dict()
        self.colors = []
        self.textures = []

        #if the node comes with attributes to initialize with then use them
        if attributes:
            self.attributes = attributes

        #else find them from maya
        else:
            self.type = cmds.getAttr(self.name + '.node_type') #bsdf, edf etc
            self.model = cmds.getAttr(self.name + '.node_model') #lambertian etc


            #add the correct attributes based on the entity defs xml
            for attribute_key in params['entityDefs'][self.model].attributes.keys():
                self.attributes[attribute_key] = ''

            for attribute_key in self.attributes.keys():
                maya_attribute = self.name + '.' + attribute_key

                #create variable to story the final string value
                attribute_value = ''

                #if the attribute is a color/entity 

                if params['entityDefs'][self.model].attributes[attribute_key].type == 'entity_picker':

                    #get attribute color value
                    attribute_color = cmds.getAttr(maya_attribute)[0]
                    connected_node = False

                    #check for connected node
                    connection = cmds.listConnections(maya_attribute)
                    if connection:
                        connected_node = connection[0]

                    #if there is a node connected
                    if connected_node:

                        #if the node is an appleseed shading node
                        if cmds.nodeType(connected_node) == 'ms_appleseed_shading_node':
                            shading_node = ShadingNode(self.params, connected_node)
                            attribute_value = shading_node.name
                            self.child_shading_nodes = self.child_shading_nodes + [shading_node] + shading_node.child_shading_nodes
                            self.colors = self.colors + shading_node.colors
                            self.textures = self.textures + shading_node.textures

                        #else if its a maya texture node
                        elif cmds.nodeType(connected_node) == 'file':
                            maya_texture_file = ms_commands.getFileTextureName(connected_node)
                            texture = ms_commands.convertTexToExr(maya_texture_file, params['absolute_tex_dir'], overwrite=self.params['overwriteExistingExrs'], pass_through=False)
                            texture_node = Texture((connected_node + '_texture'), (os.path.join(params['tex_dir'], os.path.split(texture)[1])), color_space='srgb')
                            attribute_value = (texture_node.name + '_inst')
                            self.textures = self.textures + [texture_node]

                        # if the node is unrecognized, bake it
                        else:
                            if self.params['convertShadingNodes']:
                                #convert texture and get path
                                output_texture = os.path.join(params['tex_dir'], (connected_node + '.exr'))
                                texture = convertConnectionToImage(self.name, self.attribute_key, output_texture, resolution=1024)
                                texture_node = Texture((connected_node + '_texture'), (os.path.join(params['tex_dir'], os.path.split(texture)[1])), color_space='srgb')
                                attribute_value = (texture_node.name + '_inst')
                                self.textures = self.textures + [texture_node]

                    # no node is connected, just use the color value
                    else:
                        # if that color is gray interpret the R value as a 1-dimensional value
                        if (attribute_color[0] == attribute_color[1]) and (attribute_color[0] == attribute_color[2]):
                            attribute_value = str(attribute_color[0])

                        # if its not black it must be a color so create a color node
                        elif attribute_color != (0,0,0):
                            color_name = self.name + '_' + attribute_key + '_color'
                            normalized_color = ms_commands.normalizeRGB(attribute_color)
                            color_node = Color(color_name, normalized_color[:3], normalized_color[3])
                            attribute_value = color_node.name
                            self.colors = self.colors + [color_node]

                elif params['entityDefs'][self.model].attributes[attribute_key].type == 'dropdown_list': 
                    pass
                # the node must be a text entity
                else:
                    attribute_value = str(cmds.getAttr(maya_attribute))

                # add attribute to dict
                self.attributes[attribute_key] = attribute_value

    def getChildren(self):
        return self.child_shading_nodes

    def writeXML(self, doc):
        print('writing shading node {0}'.format(self.name))
        doc.startElement('{0} name="{1}" model="{2}"'.format(self.type, self.name, self.model))

        #add the relevant parameters
        for attribute_key in self.attributes.keys():
            #only output the attribute if it has a value
            if self.attributes[attribute_key]:
                doc.appendParameter(attribute_key, self.attributes[attribute_key])

        doc.endElement(self.type)


#--------------------------------------------------------------------------------------------------
# Bsdf class.
#--------------------------------------------------------------------------------------------------

class Bsdf():
    def __init__(self, name, model, bsdf_params):
        self.name = name
        self.model = model
        self.bsdf_params = bsdf_params

    def writeXML(self, doc):
        print('writing bsdf {0}'.format(self.name))
        doc.startElement('bsdf name="{0}" model="{1}"'.format(self.name, self.model))
        for param in self.bsdf_params:
            doc.appendParameter(param, self.bsdf_params[param])
        doc.endElement('bsdf')


#--------------------------------------------------------------------------------------------------
# Edf class.
#--------------------------------------------------------------------------------------------------

class Edf():
    def __init__(self, name, model, edf_params):
        self.name = name
        self.model = model
        self.edf_params = edf_params

    def writeXML(self, doc):
        print('writing bsdf {0}'.format(self.name))
        doc.startElement('edf name="{0}" model="{1}"'.format(self.name, self.model))
        for param in self.edf_params:
            doc.appendParameter(param, self.edf_params[param])
        doc.endElement('edf')


#--------------------------------------------------------------------------------------------------
# SurfaceShader class.
#--------------------------------------------------------------------------------------------------

class SurfaceShader():
    def __init__(self, name, model, surface_shader_params=None):
        self.name = name
        self.model = model
        self.surface_shader_params = surface_shader_params

    def writeXML(self, doc):
        doc.startElement('surface_shader name="{0}" model="{1}"'.format(self.name, self.model))
        if self.model == 'constant_surface_shader':
            for param in self.surface_shader_params:
                doc.appendParameter(param, self.surface_shader_params[param])
        doc.endElement('surface_shader')


#--------------------------------------------------------------------------------------------------
# Camera class.
#--------------------------------------------------------------------------------------------------

class Camera():
    def __init__(self, params, cam):
        self.params = params
        if self.params['sceneCameraDefaultThinLens'] or cmds.getAttr(cam + '.depthOfField'):
            self.model = 'thinlens_camera'
            self.f_stop = cmds.getAttr(cam + '.fStop')
            self.focal_distance = cmds.getAttr(cam + '.focusDistance')
            self.diaphragm_blades = 0
            self.diaphragm_tilt_angle = 0.0
        else:
            self.model = 'pinhole_camera'
        self.name = cam

        maya_resolution_aspect = float(params['outputResWidth']) / float(params['outputResHeight'])
        maya_film_aspect = cmds.getAttr(cam + '.horizontalFilmAperture') / cmds.getAttr(cam + '.verticalFilmAperture')

        if maya_resolution_aspect > maya_film_aspect:
            self.film_width = float(cmds.getAttr(self.name + '.horizontalFilmAperture')) * inch_to_meter
            self.film_height = self.film_width / maya_resolution_aspect  
        else:
            self.film_height = float(cmds.getAttr(self.name + '.verticalFilmAperture')) * inch_to_meter
            self.film_width = self.film_height * maya_resolution_aspect 

        self.focal_length = float(cmds.getAttr(self.name+'.focalLength')) / 1000

        # transpose camera matrix -> XXX0, YYY0, ZZZ0, XYZ1
        m = cmds.xform(cam, query=True, ws=True, matrix=True)
        self.transform = [m[0],m[1],m[2],m[3]], [m[4],m[5],m[6],m[7]], [m[8],m[9],m[10],m[11]], [m[12],m[13],m[14],m[15]]
   
    def writeXML(self, doc):
        print('writing camera: {0}'.format(self.name))
        doc.startElement('camera name="{0}" model="{1}"'.format(self.name, self.model))

        doc.appendParameter('film_dimensions', '{0} {1}'.format(self.film_width, self.film_height))
        doc.appendParameter('focal_length', self.focal_length)

        if self.model == 'thinlens_camera':
            print('exporting ' + self.name + ' as thinlens camera')
            doc.appendParameter('focal_distance', self.focal_distance)
            doc.appendParameter('f_stop', self.f_stop)
            doc.appendParameter('diaphragm_blades', self.diaphragm_blades)
            doc.appendParameter('diaphragm_tilt_angle', self.diaphragm_tilt_angle)

        #output transform matrix
        writeTransform(doc, self.params['scene_scale'], self.name, self.params['exportCameraBlur'], self.params['motionSamples'])

        doc.endElement('camera')


#--------------------------------------------------------------------------------------------------
# Environment class.
#--------------------------------------------------------------------------------------------------

class Environment():
    def __init__(self, params, name, shader, edf):
        self.params = params
        self.name = name
        self.environment_shader = shader
        self.environment_edf = edf

    def writeXML(self, doc):
        print('writing environment: ' + self.name)
        doc.startElement('environment name="{0}" model="generic_environment"'.format(self.name))
        doc.appendParameter('environment_edf', self.environment_edf)
        #doc.appendParameter('environment_shader', self.environment_shader)

        doc.endElement('environment')


#--------------------------------------------------------------------------------------------------
# EnvironmentShader class.
#--------------------------------------------------------------------------------------------------

class EnvironmentShader():
    def __init__(self, name, edf):
        self.name = name
        self.edf = edf

    def writeXML(self, doc):
        print('writing environment shader: ' + self.name)
        doc.startElement('environment_shader name="{0}" model="edf_environment_shader"'.format(self.name))
        doc.appendParameter('environment_edf', self.edf)
        doc.endElement('environment_shader')


#--------------------------------------------------------------------------------------------------
# EnvironmentEdf class.
#--------------------------------------------------------------------------------------------------

class EnvironmentEdf():
    def __init__(self, name, model, edf_params):
        self.name = name
        self.model = model
        self.edf_params = edf_params

    def writeXML(self, doc):
        print('writing environment edf: ' + self.name)
        doc.startElement('environment_edf name="{0}" model="{1}"'.format(self.name, self.model))
        for param in self.edf_params:
            doc.appendParameter(param, self.edf_params[param])
        doc.endElement('environment_edf')


#--------------------------------------------------------------------------------------------------
# Geometry class.
#--------------------------------------------------------------------------------------------------

class Geometry():
    def __init__(self, params, name, output_file, assembly='main_assembly'):
        checkExportCancelled()
        self.params = params
        self.name = name
        self.safe_name = ms_commands.legalizeName(name)

        self.hierarchy_name = name
        self.material_nodes = []
        self.shading_nodes = []
        self.colors = []
        self.textures = []

        current_object = name
        while cmds.listRelatives(current_object, parent=True):
            current_object = cmds.listRelatives(current_object, parent=True)[0]
            self.hierarchy_name = current_object + ' ' + self.hierarchy_name
        self.output_file = output_file
        self.assembly = assembly


        # get material name
        shape_node = cmds.listRelatives(self.name, shapes=True)[0]

        #get list of unique shading engines
        shading_engines = set(cmds.listConnections(shape_node, t='shadingEngine')) 

        if shading_engines:
            for shading_engine in shading_engines:
                connected_material = cmds.listConnections(shading_engine + ".surfaceShader")
                if connected_material != None:
                    if cmds.nodeType(connected_material[0]) == 'ms_appleseed_material':
                        # this is an appleseed material
                        new_material = Material(self.params, connected_material[0])
                        self.material_nodes.append(new_material)
                        self.shading_nodes = self.shading_nodes + new_material.getShadingNodes()
                        self.colors = self.colors + new_material.colors
                        self.textures = self.textures + new_material.textures
                    else: 
                        cmds.warning("no appleseed material or shader translation connected to {0}".format(self.name))
        else:
            cmds.warning("no shading engine connected to {0}".format(self.name))

        # transpose matrix -> XXX0, YYY0, ZZZ0, XYZ1
        m = cmds.xform(name, query=True, ws=True, matrix=True)
        self.transform = [m[0],m[1],m[2],m[3]], [m[4],m[5],m[6],m[7]], [m[8],m[9],m[10],m[11]], [m[12],m[13],m[14],m[15]]
        

    def getMaterials(self):
        return self.material_nodes

    def getShadingNodes(self):
        return self.shading_nodes

    def writeXMLInstance(self, doc):
        print('writing object instance: '+ self.name)
        doc.startElement('object_instance name="{0}.0_inst" object="{1}.0"'.format(self.safe_name, self.safe_name))

        if self.params['exportTransformationBlur']:
            # write 0 transform as the assembly will handle that
            writeTransform(doc)
        else:
            writeTransform(doc, self.params['scene_scale'], self.name)

        for material in self.material_nodes:
            if material.duplicate_shaders:
                doc.appendElement('assign_material slot="{0}" side="front" material="{1}"'.format(material.name, material.name))
                doc.appendElement('assign_material slot="{0}" side="back" material="{1}"'.format(material.name, material.name))
            else:
                doc.appendElement('assign_material slot="{0}" side="front" material="{1}_front"'.format(material.name, material.name))
                doc.appendElement('assign_material slot="{0}" side="back" material="{1}_back"'.format(material.name, material.name))
        doc.endElement('object_instance')


#--------------------------------------------------------------------------------------------------
# Assembly class.
#--------------------------------------------------------------------------------------------------

class Assembly():
    def __init__(self, params, name='main_assembly', object_list=False, position_from_object=False):
        checkExportCancelled()
        self.params = params
        self.name = ms_commands.legalizeName(name)
        self.position_from_object = position_from_object
        self.light_objects = []
        self.geo_objects = []
        self.material_objects = []
        self.shading_node_objects = []
        self.color_objects = []
        self.texture_objects = []

        # add shape nodes as geo objects
        if object_list:
            for object in object_list:
                if cmds.nodeType(object) == 'mesh':
                    geo_transform = cmds.listRelatives(object, ad=True, ap=True)[0]
                    if not (geo_transform in self.geo_objects):
                        geo_filename = self.name + '.obj'
                        geo_filepath = os.path.join(self.params['geo_dir'], geo_filename)
                        self.geo_objects.append(Geometry(self.params, geo_transform, geo_filepath, self.name))
                elif cmds.nodeType(object) == 'pointLight':
                    light_transform = cmds.listRelatives(object, ad=True, ap=True)[0]
                    if not (light_transform in self.light_objects):
                        self.light_objects.append(Light(self.params, cmds.listRelatives(object, ad=True, ap=True)[0]))
                elif cmds.nodeType(object) == 'spotLight':
                    light_transform = cmds.listRelatives(object, ad=True, ap=True)[0]
                    if not (light_transform in self.light_objects):
                        light_object = Light(self.params, cmds.listRelatives(object, ad=True, ap=True)[0])
                        light_object.model = 'spot_light'
                        light_object.inner_angle = cmds.getAttr(object + '.coneAngle')
                        light_object.outer_angle = cmds.getAttr(object + '.coneAngle') + cmds.getAttr(object + '.penumbraAngle')
                        self.light_objects.append(light_object)

        # add light colors to list
        for light_object in self.light_objects:
            light_color_object = Color(light_object.color_name, light_object.color, light_object.multiplier)
            self.color_objects.append(light_color_object)

        # populate material, shading node and color list
        for geo in self.geo_objects:
            if geo.getMaterials():
                self.material_objects = self.material_objects + geo.getMaterials()
            else:
                cmds.warning("no material connected to {0}".format(geo.name))
            self.shading_node_objects = self.shading_node_objects + geo.getShadingNodes()
            self.color_objects = self.color_objects + geo.colors
            self.texture_objects = self.texture_objects + geo.textures

        # materials
        unsorted_materials = self.material_objects
        self.material_objects = dict()
        for material in unsorted_materials:
            if not material.name in self.material_objects:
                self.material_objects[material.name] = material
        self.material_objects = self.material_objects.values()

        # shading nodes
        unsorted_shading_nodes = self.shading_node_objects
        self.shading_node_objects = dict()
        for shading_node in unsorted_shading_nodes:
            if not shading_node.name in self.shading_node_objects:
                self.shading_node_objects[shading_node.name] = shading_node
        self.shading_node_objects = self.shading_node_objects.values()

        # colors
        unsorted_colors = self.color_objects
        self.color_objects = dict()
        for color in unsorted_colors:
            if not color.name in self.color_objects:
                self.color_objects[color.name] = color
        self.color_objects = self.color_objects.values()

        # textures
        unsorted_textures = self.texture_objects
        self.texture_objects = dict()
        for texture in unsorted_textures:
            if not texture.name in self.texture_objects:
                self.texture_objects[texture.name] = texture
        self.texture_objects = self.texture_objects.values()

    def writeXML(self, doc):
        print('writing assembly: {0}'.format(self.name))
        doc.startElement('assembly name="{0}"'.format(self.name))

        # write colors
        for col in self.color_objects:
            col.writeXML(doc)

        # write texture objects
        for tex in self.texture_objects:
            tex.writeXMLObject(doc)

        # write texture instances
        for tex in self.texture_objects:
            tex.writeXMLInstance(doc)

        # write bsdfs
        for shading_node in self.shading_node_objects:
            if shading_node.type == 'bsdf':
                shading_node.writeXML(doc)

        # write edfs
        for shading_node in self.shading_node_objects:
            if shading_node.type == 'edf':
                shading_node.writeXML(doc)

        # write surface shaders
        for shading_node in self.shading_node_objects:
            if shading_node.type == 'surface_shader':
                shading_node.writeXML(doc)

        # write materials
        for material in self.material_objects:
            material.writeXML(doc)

        # export and write objects
        for geo in self.geo_objects:
            file_name = ms_commands.legalizeName(geo.name)

            doc.startElement('object name="{0}" model="mesh_object"'.format(file_name))

            if  self.params['exportDeformationBlur']:
                # store the start time of the export
                start_time = cmds.currentTime(query=True)
                motion_samples = self.params['motionSamples']
                if motion_samples < 2:
                    cmds.warning('Motion samples is set too low, must be at least 2. Using 2.')
                    motion_samples = 2
                sample_interval = 1.0 / (motion_samples - 1)

                cmds.currentTime(cmds.currentTime(query=True) - 1)

                doc.startElement('parameters name="filename"')

                for i in range(motion_samples):
                    frame = start_time + sample_interval * i
                    print("exporting frame {0}".format(frame))

                    cmds.currentTime(frame)
                    cmds.refresh()

                    obj_filename = "{0}.{1:03}.obj".format(file_name, i)
                    doc.appendParameter("{0:03}".format(i), "{0}/{1}".format(self.params['geo_dir'], obj_filename))

                    # write the OBJ file to disk
                    obj_filepath = os.path.join(self.params['absolute_geo_dir'], obj_filename)
                    checkExportCancelled()
                    self.params['obj_exporter'](geo.name, obj_filepath, overwrite=True)

                doc.endElement('parameters')

                cmds.currentTime(start_time)
            else:
                obj_filename = file_name + ".obj"
                doc.appendParameter('filename', os.path.join(self.params['geo_dir'], obj_filename))

                # write the OBJ file to disk
                obj_filepath = os.path.join(self.params['absolute_geo_dir'], obj_filename)
                checkExportCancelled()
                self.params['obj_exporter'](geo.name, obj_filepath)

            self.params['progress_bar_progress'] += self.params['progress_bar_incriments']
            cmds.progressWindow(edit=True, progress=self.params['progress_bar_progress'])

            doc.endElement('object')

        # write lights
        for light_object in self.light_objects:
           light_object.writeXML(doc)

        # write geo object instances
        for geo in self.geo_objects:
            geo.writeXMLInstance(doc)

        doc.endElement('assembly')
        doc.startElement('assembly_instance name="{0}_inst" assembly="{1}"'.format(self.name, self.name))

        # if transformation blur is set output the transform with motion from the position_from_object variable
        if self.params['exportTransformationBlur']:
            writeTransform(doc, self.params['scene_scale'], self.position_from_object, True, self.params['motionSamples'])
        else:
            writeTransform(doc, self.params['scene_scale'])
        doc.endElement('assembly_instance')


#--------------------------------------------------------------------------------------------------
# Scene class.
#--------------------------------------------------------------------------------------------------

class Scene():
    def __init__(self,params):
        checkExportCancelled()
        self.params = params
        self.assembly_list = []
        self.color_objects = dict()
        self.texture_objects = dict()
        self.assembly_objects = dict()

        #setup environment 
        if self.params['environment']:
            self.environment = Environment(self.params, self.params['environment'], (self.params['environment'] + '_env_shader'), (self.params['environment'] + '_env_edf'))

            #retrieve model and param values from ui
            environment_edf_model_enum = cmds.getAttr(self.params['environment'] + '.model')
            env_edf_params = dict()
            if environment_edf_model_enum == 0:
                environment_edf_model = 'constant_environment_edf'
                environment_color = ms_commands.normalizeRGB(cmds.getAttr(self.params['environment']+'.constant_exitance')[0])
                self.addColor('constant_env_exitance', environment_color[0:3], environment_color[3])
                env_edf_params['exitance'] =  'constant_env_exitance'

            elif environment_edf_model_enum == 1:
                environment_edf_model = 'gradient_environment_edf'

                horizon_exitance = ms_commands.normalizeRGB(cmds.getAttr(self.params['environment']+'.gradient_horizon_exitance')[0])
                self.addColor('gradient_env_horizon_exitance', horizon_exitance[0:3], horizon_exitance[3])

                zenith_exitance = ms_commands.normalizeRGB(cmds.getAttr(self.params['environment']+'.gradient_zenith_exitance')[0])
                self.addColor('gradient_env_zenith_exitance', zenith_exitance[0:3], zenith_exitance[3])

                env_edf_params['horizon_exitance'] = 'gradient_env_horizon_exitance'
                env_edf_params['zenith_exitance'] = 'gradient_env_zenith_exitance'

            elif environment_edf_model_enum == 2:
                lat_long_connection = cmds.connectionInfo((self.params['environment'] + '.latitude_longitude_exitance'), sourceFromDestination=True).split('.')[0]
                environment_edf_model = 'latlong_map_environment_edf'
                if lat_long_connection:
                    if cmds.nodeType(lat_long_connection) == 'file':
                        maya_texture_file = ms_commands.getFileTextureName(lat_long_connection)
                        texture_file = ms_commands.convertTexToExr(maya_texture_file, params['absolute_tex_dir'], self.params['overwriteExistingExrs'])

                        self.addTexture(self.params['environment'] + '_latlong_edf_map', (os.path.join(params['tex_dir'], os.path.split(texture_file)[1])))
                        env_edf_params['exitance'] = self.params['environment'] + '_latlong_edf_map_inst'
                        env_edf_params['horizontal_shift'] = 0
                        env_edf_params['vertical_shift'] = 0
                else:
                    cmds.error('no texture connected to {0}.latitude_longitude_exitance'.format(self.params['environment']))

            elif environment_edf_model_enum == 3:
                mirrorball_edf_connection = cmds.connectionInfo((self.params['environment'] + '.mirror_ball_exitance'), sourceFromDestination=True).split('.')[0]
                environment_edf_model = 'mirrorball_map_environment_edf'
                if mirrorball_edf_connection:
                    if cmds.nodeType(mirrorball_edf_connection) == 'file':
                        maya_texture_name = ms_commands.getFileTextureName(mirrorball_edf_connection)
                        texture_file = ms_commands.convertTexToExr(maya_texture_name, params['absolute_tex_dir'], self.params['overwriteExistingExrs'])
                        self.addTexture(self.params['environment'] + '_mirrorball_map_environment_edf', (os.path.join(params['tex_dir'], os.path.split(texture_file)[1])))
                        env_edf_params['exitance'] = self.params['environment'] + '_mirrorball_map_environment_edf_inst'
                else:
                    cmds.error('no texture connected to {0}.mirrorball_exitance'.format(self.params['environment']))

            else:
                cmds.error('no environment model selected for ' + self.params['environment'])
            
            self.environment_edf = EnvironmentEdf((self.params['environment'] + '_env_edf'), environment_edf_model, env_edf_params)
            self.environment_shader = EnvironmentShader((self.params['environment'] + '_env_shader'), (self.params['environment'] + '_env_edf'))

        else:
            self.environment = None

    def addColor(self, name, value, multiplier=1):
        if not name in self.color_objects:
            self.color_objects[name] = Color(name, value, multiplier)

    def addTexture(self, name, file_name):
        if not name in self.texture_objects:
            self.texture_objects[name] = Texture(name, file_name)

    def writeXML(self, doc):
        print('writing scene element')

        doc.startElement('scene')

        # write current camera
        camera_instance = Camera(self.params, self.params['outputCamera'])
        camera_instance.writeXML(doc)   

        # write colors
        for col in self.color_objects:
             self.color_objects[col].writeXML(doc)

        # write texture objects
        for tex in self.texture_objects:
            self.texture_objects[tex].writeXMLObject(doc)

        # write texture instances
        for tex in self.texture_objects:
            self.texture_objects[tex].writeXMLInstance(doc)
        
        # if there is an environment write it
        if self.environment:
            self.environment_edf.writeXML(doc)
            self.environment_shader.writeXML(doc)
            self.environment.writeXML(doc)

        # write assemblies
        shape_list = cmds.ls(g=True, v=True, noIntermediate=True)
        light_list = cmds.ls(lt=True, v=True)

        self.params['progress_bar_incriments'] = 100.0 / len(shape_list)
        self.params['progress_bar_progress'] = 0

        if self.params['exportTransformationBlur']:
            for geo in shape_list:
                checkExportCancelled()
                if ms_commands.shapeIsExportable(geo):
                    # add first connected transform to the list
                    geo_transform = cmds.listRelatives(geo, ad=True, ap=True)[0]
                    geo_assembly = Assembly(self.params, geo_transform + '_assembly', [geo], geo_transform)
                    geo_assembly.writeXML(doc)

            for light in light_list:
                    light_transform = cmds.listRelatives(light, ad=True, ap=True)[0]
                    light_assembly = Assembly(self.params, light_transform + '_assembly', [light], light_transform)
                    light_assembly.writeXML(doc)
        else:
            assembly = Assembly(self.params, "assembly", light_list + shape_list)
            assembly.writeXML(doc)

        doc.endElement('scene')


#--------------------------------------------------------------------------------------------------
# Output class.
#--------------------------------------------------------------------------------------------------

class Output():
    def __init__(self, params):
        self.params = params

    def writeXML(self, doc):
        doc.startElement('output')
        doc.startElement('frame name="beauty"')
        doc.appendParameter('camera', self.params['outputCamera'])
        doc.appendParameter('color_space', self.params['outputColorSpace'])
        doc.appendParameter('resolution', '{0} {1}'.format(self.params['outputResWidth'], self.params['outputResHeight']))
        doc.endElement('frame')
        doc.endElement('output')


#--------------------------------------------------------------------------------------------------
# Configurations class.
#--------------------------------------------------------------------------------------------------

class Configurations():
    def __init__(self, params):
        self.params = params

    def writeXML(self, doc):
        print('writing configurations')

        doc.startElement("configurations")

        # add base interactive config
        doc.appendElement('configuration name="interactive" base="base_interactive"')

        #if 'customise final configuration' is set read customised values
        if self.params['customFinalConfigCheck']:
            print('writing custom final config')
            doc.startElement('configuration name="final" base="base_final"')

            if self.params['customFinalConfigEngine'] == "Path Tracing":
                engine = 'pt'
            else:
                engine = 'drt'
            doc.appendParameter('lighting_engine', engine)
            doc.appendParameter('min_samples', self.params['customFinalConfigMaxSamples'])
            doc.appendParameter('max_samples', self.params['customFinalConfigMaxSamples'])
            
            doc.startElement('parameters name="drt"')
            doc.appendParameter('dl_bsdf_samples', self.params['drtDLBSDFSamples'])
            doc.appendParameter('dl_light_samples', self.params['drtDLLightSamples'])
            doc.appendParameter('enable_ibl', self.params['drtEnableIBL'])
            doc.appendParameter('ibl_bsdf_samples', self.params['drtIBLBSDFSamples'])
            doc.appendParameter('ibl_env_samples', self.params['drtIBLEnvSamples'])
            doc.appendParameter('max_path_length', self.params['drtMaxPathLength'])
            doc.appendParameter('rr_min_path_length', self.params['drtRRMinPathLength'])
            doc.endElement("parameters")

            doc.startElement('parameters name="pt"')
            doc.appendParameter('dl_light_samples', self.params['ptDLLightSamples'])

            if self.params['ptEnableCaustics']:
                doc.appendParameter('enable_caustics', 'true')
            else:
                doc.appendParameter('enable_caustics', 'false')

            if self.params['ptEnableDL']:
                doc.appendParameter('enable_dl', 'true')
            else:
                doc.appendParameter('enable_dl', 'false')

            if self.params['ptEnableIBL']:
                doc.appendParameter('enable_ibl', 'true')
            else:
                doc.appendParameter('enable_ibl', 'false')

            doc.appendParameter('ibl_bsdf_samples', self.params['ptIBLBSDFSamples'])
            doc.appendParameter('ibl_env_samples', self.params['ptIBLEnvSamples'])
            doc.appendParameter('max_path_length', self.params['ptMaxPathLength'])

            if self.params['ptNextEventEstimation']:
                doc.appendParameter('next_event_estimation', 'true')
            else:
                doc.appendParameter('next_event_estimation', 'false')

            doc.appendParameter('rr_min_path_length', self.params['ptRRMinPathLength'])
            doc.endElement("parameters")

            doc.startElement('parameters name="generic_tile_renderer"')
            doc.appendParameter('filter_size', self.params['gtrFilterSize'])
            doc.appendParameter('max_contrast', self.params['gtrMaxContrast'])
            doc.appendParameter('max_samples', self.params['gtrMaxSamples'])
            doc.appendParameter('max_variation', self.params['gtrMaxVariation'])
            doc.appendParameter('min_samples', self.params['gtrMinSamples'])
            doc.appendParameter('sampler', self.params['gtrSampler'])
            doc.endElement('parameters')

            doc.endElement("configuration")

        else:# otherwise add default configurations
            print('writing default final config')
            doc.appendElement('configuration name="final" base="base_final"')

        doc.endElement('configurations')


#--------------------------------------------------------------------------------------------------
# Main export function.
#--------------------------------------------------------------------------------------------------

def safe_make_dirs(path):
    if not os.path.exists(path):
        os.makedirs(path)

def export(render_settings_node):
    params = getMayaParams(render_settings_node)

    # create progres bar
    params['progress_amount'] = 0
    cmds.progressWindow(title='Exporting', progress=params['progress_amount'], status='Exporting ' + render_settings_node, isInterruptable=True)


    if params['error']:
        cmds.error("error validating UI attributes")
        raise RuntimeError("check script editor for details")

    # compute the base output directory
    scene_filepath = cmds.file(q=True, sceneName=True)
    scene_basename = os.path.splitext(os.path.basename(scene_filepath))[0]
    project_directory = cmds.workspace(q=True, rd=True)
    params['outputDir'] = params['outputDir'].replace("<ProjectDir>", project_directory)
    params['outputDir'] = os.path.join(params['outputDir'], scene_basename)

    if params['exportAnimation']:
        start_frame = params['animationStartFrame']
        end_frame = params['animationEndFrame']
    else:
        start_frame = cmds.currentTime(query=True)
        end_frame = start_frame

    start_time = time.time()

    current_frame = start_frame
    original_time = cmds.currentTime(query=True)

    # loop through frames and perform export
    while (current_frame  <= end_frame):
        # todo: add check for Escape being held down here to cancel an export

        # todo: is this necessary, since we're already doing it when exporting geometry?
        cmds.currentTime(current_frame)
        frame_name = '{0:04}'.format(int(current_frame))

        # compute the output file path
        filename = params['fileName']
        filename = filename.replace("<FileName>", scene_basename)
        filename = filename.replace("#", frame_name)
        filepath = os.path.join(params['outputDir'], filename)

        # directory for geometry
        params['geo_dir'] = os.path.join(frame_name, "geometry")
        params['absolute_geo_dir'] = os.path.join(params['outputDir'], params['geo_dir'])

        # directory for textures
        params['tex_dir'] = 'textures'
        if params['animatedTextures']:
            params['tex_dir'] = os.path.join(frame_name, params['tex_dir'])
        params['absolute_tex_dir'] = os.path.join(params['outputDir'], params['tex_dir'])

        # create directories if they don't exist yet
        safe_make_dirs(params['absolute_geo_dir'])
        safe_make_dirs(params['absolute_tex_dir'])

        params['skipTextures'] = False

        print('beginning export')
        print('opening output file {0}'.format(filepath))

        doc = WriteXml(filepath)
        doc.appendLine('<?xml version="1.0" encoding="UTF-8"?>')
        doc.appendLine('<!-- File generated by Mayaseed version {0} -->'.format(ms_commands.MAYASEED_VERSION))

        print('writing project element')
        doc.startElement('project')
        scene_element = Scene(params)
        scene_element.writeXML(doc)
        output_element = Output(params)
        output_element.writeXML(doc)
        config_element = Configurations(params)
        config_element.writeXML(doc)
    
        doc.endElement('project')
        doc.close()

        current_frame += 1

        # only export textures for the first frame
        if not params['animatedTextures']:
            params['skipTextures'] = True

    cmds.currentTime(original_time)
    cmds.select(render_settings_node)

    # Compute and report export time.
    export_time = time.time() - start_time
    export_message = "Export completed in {0:.1f} seconds.".format(export_time)
    print(export_message)

    # end progress bar
    cmds.progressWindow(endProgress=1)

    cmds.confirmDialog(title="Export Completed", icon='information', message=export_message, button="OK")
