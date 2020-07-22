from dataclasses import dataclass, fields
import numpy as np
import binascii
import struct


test_dir = 'D:/D2_Datamining/Package Unpacker/2_9_0_1/output_all/city_tower_d2_0369/'


@dataclass
class ModelEntry:
    Field0: np.uint32 = np.uint32(0)
    Field4: np.uint32 = np.uint32(0)
    Field8: np.uint32 = np.uint32(0)
    FieldC: np.uint32 = np.uint32(0)
    Field10: np.uint32 = np.uint32(0)
    Field14: np.uint32 = np.uint32(0)
    Field18: np.uint32 = np.uint32(0)
    Field1C: np.uint32 = np.uint32(0)
    Field20: np.uint32 = np.uint32(0)
    Field24: np.uint32 = np.uint32(0)
    Field28: np.uint32 = np.uint32(0)


def get_hex_data(direc):
    t = open(direc, 'rb')
    h = t.read().hex().upper()
    return h


def get_flipped_hex(h, length):
    if length % 2 != 0:
        print("Flipped hex length is not even.")
        return None
    return "".join(reversed([h[:length][i:i + 2] for i in range(0, length, 2)]))


def get_header(file_hex, header):
    # The header data is 0x16F bytes long, so we need to x2 as python reads each nibble not each byte

    for f in fields(header):
        if f.type == np.uint32:
            flipped = "".join(get_flipped_hex(file_hex, 8))
            value = np.uint32(int(flipped, 16))
            setattr(header, f.name, value)
            file_hex = file_hex[8:]
    return header


hex_data = get_hex_data(test_dir + '0369-00000B77.bin')[192*2:216912*2]
entries_hex = [hex_data[i:i+48*2] for i in range(0, len(hex_data), 48*2)]
model_entries = []
for entry_hex in entries_hex:
    entry_header = ModelEntry()
    model_entries.append(get_header(entry_hex, entry_header))

print(model_entries[:3])
diffs = []
for i in range(len(model_entries)):
    if i == 0: continue
    diffs.append(model_entries[i].Field28 - model_entries[i-1].Field28)

print([x for x in sorted(diffs)])
diff_dict = {i:diffs.count(i) for i in sorted(diffs)}
print(diff_dict)


coords1 = []
coords2 = []
coords3 = []
for e in entries_hex:
    hexes = [e[:16*2], e[16*2:28*2], e[28*2:32*2]]
    for k, h in enumerate(hexes):
        # print(h)
        hex_floats = [h[i:i+8] for i in range(0, len(h), 8)]
        floats = []
        for hex_float in hex_floats:
            # We don't need to worry about flipping hex as this unpack is:
            # 1. Little Endian 2. DCBA (so reverses the direction)
            float_value = struct.unpack('f', bytes.fromhex(hex_float))[0]
            floats.append(float_value)
        # Formatting for x,y,z
        coord = floats
        # print(coords)
        if k == 0:
            coords1.append(coord)
        elif k == 1:
            coords2.append(coord)
        elif k == 2:
            coords3.append(coord)


def testing_quaternion_rotation(c, rot):
    """
    This is how the rotation in the game works.
    """
    x_old = c[0]
    y_old = c[1]
    z_old = c[2]

    x = rot[1]
    y = rot[2]
    z = rot[3]
    w = rot[0]
    print(f'Old coord: {c}')
    # Could be more efficient to use matmul??
    x_new = ((1 - 2*y*y -2*z*z)*x_old + (2*x*y + 2*w*z)*y_old + (2*x*z-2*w*y)*z_old)
    y_new = ((2*x*y - 2*w*z)*x_old + (1 - 2*x*x - 2*z*z)*y_old + (2*y*z + 2*w*x)*z_old)
    z_new = ((2*x*z + 2*w*y)*x_old + (2*y*z - 2*w*x)*y_old + (1 - 2*x*x - 2*y*y)*z_old)
    quat_rot = [x_new, y_new, z_new]
    print(f'New coord: {quat_rot}')
    return quat_rot


[print(coords1[i], coords2[i], coords3[i]) for i in range(len(coords1))]

testing_quaternion_rotation([-90.20191955566406, 64.19730377197266, -21.946565628051758], [1.3622425373667414e-15, -4.019110348349453e-15, 0.7071065306663513, 0.7071070075035095])
testing_quaternion_rotation([-90.24580383300781, 59.197303771972656, -21.946565628051758], [1.3622425373667414e-15, -4.019110348349453e-15, 0.7071065306663513, 0.7071070075035095])
testing_quaternion_rotation([-89.95956420898438, 64.19730377197266, -20.933547973632812], [1.3622425373667414e-15, -4.019110348349453e-15, 0.7071065306663513, 0.7071070075035095])
# print(sorted(coords, key=lambda x: x[2], reverse=True))
# print(sorted(rotations, key=lambda x: x[0], reverse=True))
