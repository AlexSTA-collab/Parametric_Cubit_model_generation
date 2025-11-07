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

# create a new 'EnSight Reader'
cauchy_Full_model_top_h_01case = EnSightReader(registrationName='Cauchy_Full_model_top_h_0.1.case', CaseFileName='/home/alexsta1993/Documents/STATHAS_VIENNA_POSTDOC/Applications_Examples/EdelweisModels/Cohesive_Zone_models/3D/Three_Body_Cubit/Comparizon_LinearElastic/Convergence_check/Case_a/Full_layer_models/Full_layer_Templates_angle_10/Tested_input_files_angle_10/Cauchy_Full_model_top_h_0.1.case')
cauchy_Full_model_top_h_01case.CellArrays = ['stress_top']
cauchy_Full_model_top_h_01case.PointArrays = ['displacement_top', 'reaction_top']

# set active source
SetActiveSource(cauchy_Full_model_bottom_h_01case)

# create a new 'Extract Block'
extractBlock1 = ExtractBlock(registrationName='ExtractBlock1', Input=cauchy_Full_model_bottom_h_01case)

# set active source
SetActiveSource(cauchy_Full_model_top_h_01case)

# create a new 'Extract Block'
extractBlock2 = ExtractBlock(registrationName='ExtractBlock2', Input=cauchy_Full_model_top_h_01case)

# set active source
SetActiveSource(extractBlock1)

# create a new 'Clip'
clip1 = Clip(registrationName='Clip1', Input=extractBlock1)
clip1.ClipType = 'Plane'
clip1.HyperTreeGridClipper = 'Plane'
clip1.Scalars = [None, '']

# Properties modified on clip1.ClipType
clip1.ClipType.Origin = [0.09920071718689091, -0.3838946811117305, -0.08234808744164582]

# Properties modified on clip1.ClipType
clip1.ClipType.Normal = [-0.17364818, 0.01624065529255262, -0.98480775]

# update the view to ensure updated data information
renderView1.Update()

# find source
extractBlock2 = FindSource('ExtractBlock2')

# set active source
SetActiveSource(extractBlock2)

# create a new 'Clip'
clip2 = Clip(registrationName='Clip2', Input=extractBlock2)
clip2.ClipType = 'Plane'
clip2.HyperTreeGridClipper = 'Plane'
clip2.Scalars = [None, '']

# set active source
SetActiveSource(clip2)

# Properties modified on clip2.ClipType
clip2.ClipType.Origin = [0.0, 0.0, 0.15]
clip2.ClipType.Normal = [0.17364818, 0.01624065529255262, 0.98480775]

# update the view to ensure updated data information
renderView1.Update()
