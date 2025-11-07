from pathlib import Path
import os

def write_template_file(angle, mesh_size, output_dir="."):
    output_dir = Path(output_dir).resolve()          
    parent_dir = output_dir.parent                  
    root_dir = parent_dir.parent                    # → mesh

    inp_filename = root_dir / f"Maxwell_Template_Creep_three_body_model_angle_{angle:g}_n_{mesh_size:g}.inp"
    mesh_dir = root_dir / f"angle_{angle:g}" / f"mesh_{mesh_size:g}"


    
    def relpath(file):
        # relative path from .inp location to mesh file
        return os.path.relpath(file, start=inp_filename.parent).replace("\\", "/")
    
    with open(inp_filename, "w") as f:
        f.write("*node\n")
        f.write("** Our  nodes\n")
        f.write("**\n")
        f.write(f"*include, input={relpath(mesh_dir / 'include_nodes.inp')}\n")
        
        f.write("********************************** E L E M E N T S ****************************\n")
        f.write("*element, type=C3D8, provider=edelweiss, elset=bottom-body\n")
        f.write(f"*include, input={relpath(mesh_dir / 'include_elset_bottom.inp')}\n\n")
        
        f.write("*element, type=IQuad4, provider=interfaceelement, elset=interface-body\n")
        f.write(f"*include, input={relpath(mesh_dir / 'include_elset_interface.inp')}\n\n")
        
        f.write("*element, type=C3D8, provider=edelweiss, elset=top-body\n")
        f.write(f"*include, input={relpath(mesh_dir / 'include_elset_top.inp')}\n\n")
        
        f.write("********************************** N O D E S E T S **********************************\n")
        for direction in ["Z+", "Y+", "X+", "Z-", "Y-", "X-"]:
            f.write(f"*NSET, NSET=bottom-{direction}\n")
            f.write(f"*include, input={relpath(mesh_dir / f'include_nset_bottom-{direction}.inp')}\n")
        
        for direction in ["Z-", "Y+", "X-", "Z+", "Y-", "X+"]:
            f.write(f"*NSET, NSET=top-{direction}\n")
            f.write(f"*include, input={relpath(mesh_dir / f'include_nset_top-{direction}.inp')}\n")
            
        f.write("\n*material, name=LinearElastic, id=linearelastic_body_1, provider=edelweissmaterial\n")
        f.write("**Isotropic\n**E    nu\n1.0, 0.3\n\n")

        f.write("*material, name=LinearElastic, id=linearelastic_body_2, provider=edelweissmaterial\n")
        f.write("**Isotropic\n**E    nu\n1.0, 0.3\n\n")

        f.write("*material, name=marmotViscoElasticInterfacematerial , id=ViscoElasticInterfaceMaterial, provider = edelweissmaterial\n")
        f.write("** E_M, nu_M,  E_I, nu_I,  E_0, nu_0,   h,   m_Ju,  n_Ju, nKelvin_Ju, minTau_Ju,   m_Js,    n_Js, nKelvin_Js,  minTau_Js, timeToDays, MaterialID \n")
        f.write(f" $E_M,  0.3, $E_I,  0.3, $E_0,  0.3,  $h,  $m_Ju, $n_Ju,          1,      1e-2,  $m_Js,   $n_Js,          1,       1e-2,        1e0,         0\n\n")
        f.write("*section, name=section1, material=linearelastic_body_2, type=solid\n")
        f.write("bottom-body\n\n")

        f.write("*section, name=section2, material=linearelastic_body_1, type=solid\n")
        f.write("top-body\n\n")

        f.write("*section, name=section3, material=ViscoElasticInterfaceMaterial, type=solid\n")
        f.write("interface-body\n\n")

        f.write("*job, name=IQuad4job, domain=3d\n")
        f.write("*solver, solver=NIST, name=theSolver\n\n")

        f.write("*fieldOutput\n")
        f.write("create=perNode, elSet=top-body, field=displacement, result=U, name=displacement_top\n")
        f.write("create=perNode, elSet=top-body, field=displacement, result=P, name=reaction_top\n")
        f.write("create=perNode, elSet=bottom-body, field=displacement, result=U, name=displacement_bottom\n")
        f.write("create=perNode, elSet=bottom-body, field=displacement, result=P, name=reaction_bottom\n")
        f.write("create=perNode, elSet=interface-body, field=displacement, result=U, name=displacement_interface\n")
        f.write("create=perElement, elSet=top-body, quadraturePoint=0:8, result=stress , name=stress_top, f(x)='np.mean(x,axis=1)' \n")
        f.write("create=perElement, elSet=bottom-body, quadraturePoint=0:8, result=stress , name=stress_bottom, f(x)='np.mean(x,axis=1)' \n\n")
        f.write("create=perElement, elSet=interface-body, quadraturePoint=0:4, result=force , name=force_interface, f(x)='np.mean(x,axis=1)' \n")
        f.write("create=perElement, elSet=interface-body, quadraturePoint=0:4, result=surface stress , name=surface_stress_interface, f(x)='np.mean(x,axis=1)' \n\n")


        f.write("*output, type=ensight, name=Cohesive_zone_model_interface\n")
        f.write("create=perNode, fieldOutput=displacement_interface\n")
        f.write("create=perElement, fieldOutput=force_interface\n")
        f.write("create=perElement, fieldOutput=surface_stress_interface\n")
        f.write("configuration, overwrite=yes\n\n")

        f.write("*output, type=ensight, name=Cohesive_zone_model_top\n")
        f.write("create=perNode, fieldOutput=displacement_top\n")
        f.write("create=perNode,  fieldOutput=reaction_top\n")
        f.write("create=perElement, fieldOutput=stress_top\n")
        f.write("configuration, overwrite=yes\n\n")

        f.write("*output, type=ensight, name=Cohesive_zone_model_bottom\n")
        f.write("create=perNode,  fieldOutput=displacement_bottom\n")
        f.write("create=perNode,  fieldOutput=reaction_bottom\n")
        f.write("create=perElement, fieldOutput=stress_bottom\n")
        f.write("configuration, overwrite=yes\n\n")
        #first step fast loading
        f.write("*step, solver=theSolver, maxInc=1, minInc=1, maxNumInc=1000, maxIter=1000, stepLength=1e-8\n")
        f.write("options, category=NISTSolver, extrapolation=off\n\n")

        f.write("dirichlet, name = bottom, nSet = bottom-Z-, field=displacement, 1=0, 2=0, 3=0, f(t)=t\n")
        f.write("nodeforces, name = TopF, nSet = top-Z+, field=displacement, 1=1e-4, f(t)=t\n")
        f.write("dirichlet, name = top, nSet = top-Z+, field=displacement, 2=0, 3=0, f(t)=t\n")
        
        #Second step keep load constant
        f.write("*step, solver=theSolver, maxInc=0.025, minInc=0.0125, maxNumInc=1000, maxIter=1000, stepLength=0.1\n")
        f.write("options, category=NISTSolver, extrapolation=off\n\n")

        f.write("dirichlet, name = bottom, nSet = bottom-Z-, field=displacement, 1=0, 2=0, 3=0, f(t)=t\n")
        f.write("nodeforces, name = TopF, nSet = top-Z+, field=displacement, 1=0, f(t)=1\n")
        f.write("dirichlet, name = top, nSet = top-Z+, field=displacement, 2=0, 3=0, f(t)=t\n")
    print(f"✅ Template file '{inp_filename}' written successfully with.")


if __name__ == "__main__":
    angle = float(sys.argv[3])
    mesh_size = float(sys.argv[4])
    write_template_file(angle, mesh_size)
