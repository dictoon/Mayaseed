# mayaToAppleseed.py 

# WORK IN PROGRESS!!

# uncomment the next few lines replace the path and run them in the maya script editor to launch the script 
#--------------------maya command (python)--------------------
#import sys
#sys.path.append('/projects/mayaToAppleseed')
#import mayaToAppleseed
#reload(mayaToAppleseed)
#mayaToAppleseed.m2s()
#-------------------------------------------------------------


import maya.cmds as cmds
import os
import re

script_name = "mayaToAppleseed.py"
version = "0.01"
more_info_url = "https://github.com/jonathantopf/mayaToAppleseed"

#
# load params function
#

def getMayaParams():
    #comile regular expression to check for non numeric chracters
    is_numeric = re.compile('^[0-9]+$')
    
    params = {'error':False}
    # custom intercative config
    params['customInteractiveConfigCheck'] = cmds.checkBox('m2s_customInteractiveConfigCheck', query=True, value=True)
    params['customInteractiveConfigEngine'] = cmds.optionMenu('m2s_customInteractiveConfigEngine', query=True, value=True)
    params['customInteractiveConfigMinSamples'] = cmds.textField('m2s_customInteractiveConfigMinSamples', query=True, text=True)
    if not is_numeric.match(params['customInteractiveConfigMinSamples']):
        params['error'] = True
        print('ERROR: Custom Interactive Config Min Samples may only contain whole numbers')
    params['customInteractiveConfigMaxSamples'] = cmds.textField('m2s_customInteractiveConfigMaxSamples', query=True, text=True)
    if not is_numeric.match(params['customInteractiveConfigMaxSamples']):
        params['error'] = True
        print('ERROR: Custom Interactive Config Max Samples is non int')
    # custom Final config
    params['customFinalConfigCheck'] = cmds.checkBox('m2s_customFinalConfigCheck', query=True, value=True)
    params['customFinalConfigEngine'] = cmds.optionMenu('m2s_customFinalConfigEngine', query=True, value=True)
    params['customFinalConfigMinSamples'] = cmds.textField('m2s_customFinalConfigMinSamples', query=True, text=True)
    if not is_numeric.match(params['customFinalConfigMinSamples']):
        params['error'] = True
        print('ERROR: Custom Final Config Min Samples may only contain whole numbers')
    params['customFinalConfigMaxSamples'] = cmds.textField('m2s_customInteractiveConfigMaxSamples', query=True, text=True)
    if not is_numeric.match(params['customFinalConfigMaxSamples']):
        params['error'] = True
        print('ERROR: Custom Final Config Max Samples is non int')

    return(params)

#
# maya shader object --
#

class mayaShader(): #object transform name
    name = ""
    color = [0.5,0.5,0.5]
    color_texture = ""
    specular_color = [0.5,0.5,0.5]
    specular_color_texture = ""
    
    def __init__(self, obj): 
        #get shader name from transform name
        shape = cmds.listRelatives(obj, s=True)[0]
        shadingEngine = cmds.listConnections(shape, t='shadingEngine')[0]
        shader = cmds.connectionInfo((shadingEngine + ".surfaceShader"),sourceFromDestination=True).split('.')[0] #find the attribute the surface shader is plugged into athen split off the attribute name to leave the shader name
        self.name = shader
        
#
# maya camera object --
#

class mayaCamera(): #(camera_name)
    name = ""
    model = "pinhole_camera"
    controller_target = [0, 0, 0]
    film_dimensions = [1.417 , 0.945]
    focal_length = 35.000
    transform = [1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1] # XXX0, YYY0, ZZZ0, XYZ1
   
    def __init__(self, cam):
        self.name = cam
        self.film_dimensions[0] = cmds.getAttr(cam+'.horizontalFilmAperture')
        self.film_dimensions[1] = cmds.getAttr(cam+'.verticalFilmAperture')
        self.focal_length = cmds.getAttr(cam+'.focalLength')
        # transpose camera matrix -> XXX0, YYY0, ZZZ0, XYZ1
        m = cmds.getAttr(cam+'.matrix')
        self.transform = [m[0],m[1],m[2],m[3]], [m[4],m[5],m[6],m[7]], [m[8],m[9],m[10],m[11]], [m[12],m[13],m[14],m[15]]
    
    def info(self):
        print("name: {0}".format(self.name))
        print("camera model: {0}".format(self.model))
        print("controller_target: {0}".format(self.controller_target))
        print("film dimensions: {0}".format(self.film_dimensions))
        print("focal length: {0}".format(self.focal_length))
        print("transform matrix: {0} # XXX0 YYY0 ZZZ0 XYZ1\n".format(self.transform))

#
# maya geometry object --
#

class mayaGeometry(): # (object_transfrm_name, obj_file)
    name = ""
    outPutFile = ""
    assembly = "assembly"
    shader = ""
    transform = [1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1] # XXX0, YYY0, ZZZ0, XYZ1
    
    def __init__(self,obj, obj_file):
        self.name = obj
        self.outPutFile = obj_file
        self.assembly = cmds.listSets(object=obj)[0]
        # get shader name
        shape = cmds.listRelatives(obj, s=True)[0]
        shadingEngine = cmds.listConnections(shape, t='shadingEngine')[0]
        shader_name = cmds.connectionInfo((shadingEngine + ".surfaceShader"),sourceFromDestination=True).split('.')[0] #find the attribute the surface shader is plugged into athen split off the attribute name to leave the shader name
        self.shader = shader_name
        # transpose camera matrix -> XXX0, YYY0, ZZZ0, XYZ1
        m = cmds.getAttr(obj+'.matrix')
        self.transform = [m[0],m[1],m[2],m[3]], [m[4],m[5],m[6],m[7]], [m[8],m[9],m[10],m[11]], [m[12],m[13],m[14],m[15]]
        
    def info(self):
        print("name: {0}".format(self.name))
        print("output file: {0}".format(self.outPutFile))
        print("assembly name: {0}".format(self.assembly))
        print("shader name: {0}".format(self.shader))
        print("transform matrix: {0} # XXX0 YYY0 ZZZ0 XYZ1\n".format(self.transform))
	
#
# scene object --
#

class configurations():
    params = None
    def __init__(self, params):
        self.params = params
    def writeXML(self,doc):
        doc.startElement("<configurations>")
        #if 'customise interactive configuration' is set read customised values
        if self.params['customInteractiveConfigCheck']:
            doc.startElement("<configuration name=\"interactive\"> base=\"base_interactive\">")
            engine = ""
            if self.params['customInteractiveConfigEngine'] == "Path Tracing":
                engine = "pt"
            else:
                engine = "drt"
            doc.appendElement("<parameter name=\"lighting_engine\" value=\"{0}\"/>".format(engine))
            doc.appendElement("<parameter name=\"min_samples\" value=\"{0}\" />".format(self.params['customInteractiveConfigMinSamples']))
            doc.appendElement("<parameter name=\"max_samples\" value=\"{0}\" />".format(self.params['customInteractiveConfigMaxSamples']))
            doc.endElement("</configuration>")
        else:# otherwise add default configurations
            doc.appendElement("<configuration name=\"interactive\" base=\"base_final\" />")
  
        #if 'customise final configuration' is set read customised values
        if cmds.checkBox('m2s_customFinalConfigCheck', query=True, value=True) == True:
            doc.startElement("<configuration name=\"final\"> base=\"base_final\">")
            engine = ""
            if cmds.optionMenu('m2s_customFinalConfigEngine', query=True, value=True) == "Path Tracing":
                engine = "pt"
            else:
                engine = "drt"
            doc.appendElement("<parameter name=\"lighting_engine\" value=\"{0}\"/>".format(engine))
            doc.appendElement("<parameter name=\"min_samples\" value=\"{0}\" />".format(self.params['customFinalConfigMinSamples']))
            doc.appendElement("<parameter name=\"max_samples\" value=\"{0}\" />".format(self.params['customFinalConfigMaxSamples']))
            doc.endElement("</configuration>")
        else:# otherwise add default configurations
            doc.appendElement("<configuration name=\"final\" base=\"base_interactive\" />")
        # begin adding custom configurations
        doc.endElement("</configurations>")
	

#
# writeXml Object --
#

class writeXml(): #(file_path)
    file_path = "/"
    indentation_level = 0
    spaces_per_indentation_level = 4
    file_object = None
    
    def __init__(self, f_path):
        self.file_path = f_path
        try:
            self.file_object = open(self.file_path, 'w') #open file for editing

        except IOError:
            raise RuntimeError("IO error: file not accesable")
            return
        
    def startElement(self,str):
        self.file_object.write(((self.indentation_level * self.spaces_per_indentation_level) * " ") + str + "\n")
        self.indentation_level += 1
        
    def endElement(self, str):
        self.indentation_level -= 1
        self.file_object.write(((self.indentation_level * self.spaces_per_indentation_level) * " ") + str + "\n")
        
    def appendElement(self, str):
        self.file_object.write(((self.indentation_level * self.spaces_per_indentation_level) * " ") + str + "\n")
        
    def close(self):
        self.file_object.close() #close file



#
# build and export
#

def export():
    params = getMayaParams()
    if not params['error']:
        print('--exporting to appleseed--')
        doc = writeXml("/projects/test.xml")
        doc.appendElement("<?xml version=\"1.0\" encoding=\"UTF-8\"?>") # XML format string
        doc.appendElement("<!-- File generated by {0} version {1} visit {2} for more info -->\n".format(script_name, version, more_info_url))
        doc.startElement("<project>")
        config = configurations(params)
        config.writeXML(doc)
    
        doc.endElement("</project>")
        doc.close()
        print "--export finished--"
    else:
        raise RuntimeError('check script editor for details')
















#
# show ui --
#

def m2s():
    mayaToAppleseedUi = cmds.loadUI(f="{0}/mayaToAppleseed.ui".format(os.path.dirname(__file__)))    
    cmds.showWindow(mayaToAppleseedUi)



#
# read maya scene and generate objects --
#

# create and populate a list of mayaCamera objects
cam_list = []
for c in cmds.ls(ca=True, v=True):
    cam_list.append(mayaCamera(c))

# create and polulate a list of mayaGeometry objects
shape_list = cmds.ls(g=True, v=True) # get maya geometry
geo_transform_list = []
for g in shape_list:
    geo_transform_list.append(cmds.listRelatives(g, ad=True, ap=True)[0]) # add first connected transform to the list
