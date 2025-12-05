from pathlib import Path
import os

def write_template_file(angle, height, output_dir="."):
    output_dir = Path(output_dir).resolve()          
    parent_dir = output_dir.parent                  
    root_dir = parent_dir.parent                    # → mesh

    inp_filename = root_dir / f"LinearElastic_Full_Cauchy_Template_three_body_model_angle_{angle:g}_h_{height:g}.inp"
    # Path should be relative to template location, not including angle directory
    # Templates are deployed to family/angle_X/*_templates/ and include files are in height_X/
    mesh_dir_relative = f"height_{height:g}"
    
    def relpath(filename):
        # Return simple relative path: height_X/filename
        return f"{mesh_dir_relative}/{filename}"
    
    with open(inp_filename, "w") as f:
        f.write("*node\n")
        f.write("** Our  nodes\n")
        f.write("**\n")
        f.write(f"*include, input={relpath('include_nodes.inp')}\n")
        
        f.write("********************************** E L E M E N T S ****************************\n")
        f.write("*element, type=C3D8, provider=edelweiss, elset=bottom-body\n")
        f.write(f"*include, input={relpath('include_elset_bottom.inp')}\n\n")
        
        f.write("*element, type=C3D8, provider=edelweiss,, elset=interface-body\n")
        f.write(f"*include, input={relpath('include_elset_interface.inp')}\n\n")
        
        f.write("*element, type=C3D8, provider=edelweiss, elset=top-body\n")
        f.write(f"*include, input={relpath('include_elset_top.inp')}\n\n")
        
        f.write("********************************** N O D E S E T S **********************************\n")
        for direction in ["Z+", "Y+", "X+", "Z-", "Y-", "X-"]:
            f.write(f"*NSET, NSET=bottom-{direction}\n")
            f.write(f"*include, input={relpath(f'include_nset_bottom-{direction}.inp')}\n")
        
        for direction in ["Z-", "Y+", "X-", "Z+", "Y-", "X+"]:
            f.write(f"*NSET, NSET=top-{direction}\n")
            f.write(f"*include, input={relpath(f'include_nset_top-{direction}.inp')}\n")

        for direction in ["Z-", "Y+", "X-", "Z+", "Y-", "X+"]:
            f.write(f"*NSET, NSET=interphase-{direction}\n")
            f.write(f"*include, input={relpath(f'include_nset_interphase-{direction}.inp')}\n")

        f.write("\n*material, name=LinearElastic, id=linearelastic_body_1, provider=edelweiss\n")
        f.write("**Isotropic\n**E_M    nu\n $E_M, 0.3\n\n")

        f.write("\n*material, name=LinearElastic, id=linearelastic_body_2, provider=edelweiss\n")
        f.write("**Isotropic\n**E_I    nu\n $E_I, 0.3\n\n")

        f.write("\n*material, name=LinearElastic, id=ElasticInterfaceMaterial, provider=edelweiss\n")
        f.write(f" **Isotropic\n** E_0, nu_0\n $E_0, 0.3\n\n")
        
        f.write("*section, name=section1, material=linearelastic_body_2, type=solid\n")
        f.write("bottom-body\n\n")

        f.write("*section, name=section2, material=linearelastic_body_1, type=solid\n")
        f.write("top-body\n\n")

        f.write("*section, name=section3, material=ElasticInterfaceMaterial, type=solid\n")
        f.write("interface-body\n\n")

        f.write("*job, name=InterfaceModel_job, domain=3d\n")
        f.write("*solver, solver=NISTParallel, name=theSolver\n\n")

        f.write("*fieldOutput\n")
        f.write("create=perNode, elSet=top-body, field=displacement, result=U, name=displacement_top\n")
        f.write("create=perNode, elSet=top-body, field=displacement, result=P, name=reaction_top\n")
        f.write("create=perNode, elSet=bottom-body, field=displacement, result=U, name=displacement_bottom\n")
        f.write("create=perNode, elSet=bottom-body, field=displacement, result=P, name=reaction_bottom\n")
        f.write("create=perNode, elSet=interface-body, field=displacement, result=U, name=displacement_interface\n")
        f.write("create=perElement, elSet=top-body, quadraturePoint=0:8, result=stress , name=stress_top, f(x)='np.mean(x,axis=1)' \n")
        f.write("create=perElement, elSet=bottom-body, quadraturePoint=0:8, result=stress , name=stress_bottom, f(x)='np.mean(x,axis=1)' \n\n")
        f.write("create=perElement, elSet=interface-body, quadraturePoint=0:8, result=stress, name=stress_interface, f(x)='np.mean(x,axis=1)' \n\n")

        f.write("*output, type=ensight, name=Cauchy_Full_model_interface_${h}\n")
        f.write("create=perNode, fieldOutput=displacement_interface\n")
        f.write("create=perElement, fieldOutput=stress_interface\n")
        f.write("configuration, overwrite=yes\n\n")

        f.write("*output, type=ensight, name=Cauchy_Full_model_top_${h}\n")
        f.write("create=perNode, fieldOutput=displacement_top\n")
        f.write("create=perNode,  fieldOutput=reaction_top\n")
        f.write("create=perElement, fieldOutput=stress_top\n")
        f.write("configuration, overwrite=yes\n\n")

        f.write("*output, type=ensight, name=Cauchy_Full_model_bottom_${h}\n")
        f.write("create=perNode,  fieldOutput=displacement_bottom\n")
        f.write("create=perNode,  fieldOutput=reaction_bottom\n")
        f.write("create=perElement, fieldOutput=stress_bottom\n")
        f.write("configuration, overwrite=yes\n\n")
        
        #first step apply displacement
        f.write("*step, solver=theSolver, maxInc=1, minInc=1, maxNumInc=1000, maxIter=1000, stepLength=1.0\n")
        f.write("options, category=NISTSolver, extrapolation=off\n") 
        
        f.write("dirichlet, name = bottom,   nSet = bottom-Z-,  field=displacement, 1=0., 2=0, 3=0, f(t)=t\n")
        f.write("dirichlet, name = top,      nSet = top-Z+,  field=displacement, 1=1e-2, 2=0, 3=0, f(t)=t\n")
        f.write("dirichlet, name = bottom-LX,   nSet = bottom-X-,  field=displacement, 2=0, 3=0, f(t)=t\n")
        f.write("dirichlet, name = bottom-RX,   nSet = bottom-X+,  field=displacement, 2=0, 3=0, f(t)=t\n")
        f.write("dirichlet, name = bottom-FY,   nSet = bottom-Y-,  field=displacement, 2=0, 3=0, f(t)=t\n")
        f.write("dirichlet, name = bottom-BY,   nSet = bottom-Y+,  field=displacement, 2=0, 3=0, f(t)=t\n")
        f.write("dirichlet, name = top-LX,   nSet = top-X-,  field=displacement, 2=0, 3=0, f(t)=t\n")
        f.write("dirichlet, name = top-RX,   nSet = top-X+,  field=displacement, 2=0, 3=0, f(t)=t\n")
        f.write("dirichlet, name = top-FY,   nSet = top-Y-,  field=displacement, 2=0, 3=0, f(t)=t\n")
        f.write("dirichlet, name = top-BY,   nSet = top-Y+,  field=displacement, 2=0, 3=0, f(t)=t\n")
        f.write("dirichlet, name = interphase-LX,   nSet = interphase-X-,  field=displacement, 2=0, 3=0, f(t)=t\n")
        f.write("dirichlet, name = interphase-RX,   nSet = interphase-X+,  field=displacement, 2=0, 3=0, f(t)=t\n")
        f.write("dirichlet, name = interphase-FY,   nSet = interphase-Y-,  field=displacement, 2=0, 3=0, f(t)=t\n")
        f.write("dirichlet, name = interphase-BY,   nSet = interphase-Y+,  field=displacement, 2=0, 3=0, f(t)=t\n")


    print(f"✅ Template file '{inp_filename}' written successfully with.")


if __name__ == "__main__":
    angle = float(sys.argv[3])
    height = float(sys.argv[4])
    write_template_file(angle, mesh_size)
