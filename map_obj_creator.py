import os
import pkg_db
import struct
pkgs_dir = 'D:/D2_Datamining/Package Unpacker/2_9_0_1/output_all/'

package_dir_list = ['eden_06a1',
                    'eden_06a2',
                    'eden_036a']  # With / at end


def get_hex_data(direc):
    t = open(direc, 'rb')
    h = t.read().hex().upper()
    return h


def file_to_coords(file_hex):
    hex_floats = [file_hex[i:i+8] for i in range(0, len(file_hex), 8)]
    floats = []
    for hex_float in hex_floats:
        # We don't need to worry about flipping hex as this unpack is:
        # 1. Little Endian 2. DCBA (so reverses the direction)
        float_value = struct.unpack('f', bytes.fromhex(hex_float))[0]
        floats.append(str(round(float_value, 2)))
    # Formatting for x,y,z
    coords = [floats[i:i+3] for i in range(0, len(floats), 3)]
    return coords


def coords_to_obj(coords, pkg, file_name):
    lines_to_write = []
    #print(f'Number of coords {len(coords)}')
    for coord in coords:
        if len(coord) != 3:
            continue
        line = f'v {coord[0]} {coord[1]} {coord[2]}\n'  # Coords
        if 'nan' not in line:
            # We don't want a coord that just stacks up at (0, 0, 0)
            if line.count("0.0") != 3:
                lines_to_write.append(line)

    with open(f'Objects/{pkg}/{file_name}.obj', 'w') as q:
        q.write(f'o {file_name}\n')
        for line in lines_to_write:
            q.write(line)

    print(f"\nWritten {len(lines_to_write)} points to {file_name}.obj")


pkg_db.start_db_connection('2_9_0_1')

for pkg in package_dir_list:
    try:
        os.mkdir("Objects/")
        os.mkdir("Objects/" + pkg)
    except FileExistsError:
        try:
            os.mkdir("Objects/" + pkg)
        except FileExistsError:

            pass
    entries = {x: y for x, y in pkg_db.get_entries_from_table(pkg, 'FileName, FileType')}

    for file in os.listdir(pkgs_dir + pkg):
        file_name = file.split('.')[0]
        if entries[file_name] == "Mapping Data":
            file_hex = get_hex_data(pkgs_dir + pkg + '/' + file)
            coords = file_to_coords(file_hex)
            coords_to_obj(coords, pkg, file_name)
