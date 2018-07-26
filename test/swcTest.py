import files

def run(path='data/swcTest/7f_ss_cell1_step0_av2.tif_x122_y34_z26_app2.swc'):
    tree = files.importFromSWC(path)
    print (tree)
    return True
