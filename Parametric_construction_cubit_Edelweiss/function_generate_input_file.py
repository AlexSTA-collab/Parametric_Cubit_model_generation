import os

def write_input_file(E0, h, angle, mesh_size, output_dir="."):
    mesh_dir = os.path.abspath(os.path.join(output_dir, "..", ".."))  # → angle/mesh_size/
    inp_filename = os.path.join(output_dir, f"three_body_model_E0_{E0:.1e}_h_{h:.1e}_angle_{angle:02d}_n_{mesh_size:03d}.inp")

    with open(inp_filename, "w") as f:
        f.write("*node\n")
        f.write("** Our  nodes\n")
        f.write("**\n")
        f.write("*include, input=" + os.path.join(mesh_dir, "include_nodes.inp") + "\n")

        f.write("********************************** E L E M E N T S ****************************\n")
        f.write("*element, type=Hexa8, provider=displacementelement, elset=bottom-body\n")
        f.write("*include, input=" + os.path.join(mesh_dir, "include_elset_bottom.inp") + "\n\n")

        f.write("*element, type=IQuad4, provider=interfaceelement, elset=interface-body\n")
        f.write("*include, input=" + os.path.join(mesh_dir, "include_elset_interface.inp") + "\n\n")

        f.write("*element, type=Hexa8, provider=displacementelement, elset=top-body\n")
        f.write("*include, input=" + os.path.join(mesh_dir, "include_elset_top.inp") + "\n\n")

        f.write("********************************** N O D E S E T S **********************************\n")
        for direction in ["Z+", "Y+", "X+", "Z-", "Y-", "X-"]:
            f.write(f"*NSET, NSET=bottom-{direction}\n")
            f.write("*include, input=" + os.path.join(mesh_dir, f"include_nset_bottom-{direction}.inp") + "\n")
        for direction in ["Z-", "Y+", "X-", "Z+", "Y-", "X+"]:
            f.write(f"*NSET, NSET=top-{direction}\n")
            f.write("*include, input=" + os.path.join(mesh_dir, f"include_nset_top-{direction}.inp") + "\n")

        f.write("\n*material, name=LinearElastic, id=linearelastic_body_1, provider=edelweissmaterial\n")
        f.write("**Isotropic\n**E    nu\n1.0, 0.3\n\n")

        f.write("*material, name=LinearElastic, id=linearelastic_body_2, provider=edelweissmaterial\n")
        f.write("**Isotropic\n**E    nu\n1.0, 0.3\n\n")

        f.write("*material, name=marmotinterfacematerial, id=ElasticInterfaceMaterial, provider = edelweissmaterial\n")
        f.write("** E_M, nu_M, E_I, nu_I, E_0 , nu_0, h, MaterialID \n")
        f.write(f"1.0, 0.3, 1.0, 0.3, {E0}, 0.3, {h}, 0\n\n")

        f.write("*section, name=section1, material=linearelastic_body_2, type=solid\n")
        f.write("bottom-body\n\n")

        f.write("*section, name=section2, material=linearelastic_body_1, type=solid\n")
        f.write("top-body\n\n")

        f.write("*section, name=section3, material=ElasticInterfaceMaterial, type=solid\n")
        f.write("interface-body\n\n")

        f.write("*job, name=IQuad4job, domain=3d\n")
        f.write("*solver, solver=NIST, name=theSolver\n\n")

        f.write("*fieldOutput\n")
        f.write("create=perNode, elSet=top-body, field=displacement, result=U, name=displacement_top\n")
        f.write("create=perNode, elSet=bottom-body, field=displacement, result=U, name=displacement_bottom\n")
        f.write("create=perNode, elSet=interface-body, field=displacement, result=U, name=displacement_interface\n")
        f.write("create=perElement, elSet=top-body, quadraturePoint=0:8, result=stress , name=stress_top, f(x)='np.mean(x,axis=1)' \n")
        f.write("create=perElement, elSet=bottom-body, quadraturePoint=0:8, result=stress , name=stress_bottom, f(x)='np.mean(x,axis=1)' \n\n")

        f.write("*output, type=ensight, name=Cohesive_zone_model_interface\n")
        f.write("create=perNode, fieldOutput=displacement_interface\n")
        f.write("configuration, overwrite=yes\n\n")

        f.write("*output, type=ensight, name=Cohesive_zone_model_top\n")
        f.write("create=perNode, fieldOutput=displacement_top\n")
        f.write("create=perElement, fieldOutput=stress_top\n")
        f.write("configuration, overwrite=yes\n\n")

        f.write("*output, type=ensight, name=Cohesive_zone_model_bottom\n")
        f.write("create=perNode,  fieldOutput=displacement_bottom\n")
        f.write("create=perElement, fieldOutput=stress_bottom\n")
        f.write("configuration, overwrite=yes\n\n")

        f.write("*step, solver=theSolver, maxInc=1e-1, minInc=1e-3, maxNumInc=1000, maxIter=1000, stepLength=1\n")
        f.write("options, category=NISTSolver, extrapolation=off\n\n")

        f.write("dirichlet, name = bottom,       nSet = bottom-Z-,  field=displacement, 1=1, 2=0, 3=0\n")
        f.write("dirichlet, name = top,          nSet = top-Z+,     field=displacement, 1=-1, 2=0, 3=0\n")

    print(f"✅ Input file '{inp_filename}' written successfully with E0={E0}, h={h}.")


if __name__ == "__main__":
    E_0 = float(sys.argv[1])
    h = float(sys.argv[2])
    angle = float(sys.argv[3])
    mesh_size = float(sys.argv[4])
    write_input_file(E0, h, angle, mesh_size)
