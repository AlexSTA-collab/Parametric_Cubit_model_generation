# trace generated using paraview version 5.11.2
#import paraview
#paraview.compatibility.major = 5
#paraview.compatibility.minor = 11

#### import the simple module from the paraview
from paraview.simple import *
#### disable automatic camera reset on 'Show'
paraview.simple._DisableFirstRenderCameraReset()

# create a new 'EnSight Reader'
cauchy_Full_model_bottom_h_01case = EnSightReader(registrationName='Cauchy_Full_model_bottom_h_0.1.case', CaseFileName='/home/alexsta1993/Documents/STATHAS_VIENNA_POSTDOC/Applications_Examples/EdelweisModels/Cohesive_Zone_models/3D/Three_Body_Cubit/Comparizon_LinearElastic/Convergence_check/Case_a/Full_layer_models/Full_layer_Templates_angle_10/Tested_input_files_angle_10/Cauchy_Full_model_bottom_h_0.1.case')
cauchy_Full_model_bottom_h_01case.CellArrays = ['stress_bottom']
cauchy_Full_model_bottom_h_01case.PointArrays = ['displacement_bottom', 'reaction_bottom']

# get animation scene
animationScene1 = GetAnimationScene()

# get the time-keeper
timeKeeper1 = GetTimeKeeper()

# create a new 'Extract Block'
extractBlock1 = ExtractBlock(registrationName='ExtractBlock1', Input=cauchy_Full_model_bottom_h_01case)
extractBlock1.Selectors = ["/bottom-body"]
extractBlock1.UpdatePipeline()

# show data in view
extractBlock1Display = Show(extractBlock1, renderView1, 'UnstructuredGridRepresentation')
