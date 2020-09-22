import gf


def get_model_textures(model_hash):
    file = gf.get_file_from_hash(gf.get_flipped_hex(model_hash, 8))
    pkg = gf.get_pkg_name(file)
    print(f'{model_hash} mf1 C:/d2_output/{pkg}/{file}.bin')
    mf1_hex = gf.get_hex_data(f'C:/d2_output/{pkg}/{file}.bin')
    file = gf.get_file_from_hash(gf.get_flipped_hex(mf1_hex[16:24], 8))
    pkg = gf.get_pkg_name(file)
    print(f'{model_hash} mf2 C:/d2_output/{pkg}/{file}.bin')
    mf2_hex = gf.get_hex_data(f'C:/d2_output/{pkg}/{file}.bin')
    texture_count = int(gf.get_flipped_hex(mf2_hex[80*2:84*2], 8), 16)
    texture_id_entries = [[int(gf.get_flipped_hex(mf2_hex[i:i+4], 4), 16), mf2_hex[i+4:i+8], mf2_hex[i+8:i+12]] for i in range(96*2, 96*2+texture_count*16, 16)]
    texture_entries = [mf1_hex[i:i+8] for i in range(176*2, 176*2+texture_count*8, 8)]
    relevant_textures = {}
    for i, entry in enumerate(texture_id_entries):
        if entry[2] == '7B00':
            relevant_textures[entry[0]] = gf.get_file_from_hash(gf.get_flipped_hex(texture_entries[i], 8))
    print(relevant_textures)


if __name__ == '__main__':
    get_model_textures('CCC7F380')
    get_model_textures('0A34ED80')
    # get_model_textures('4922ED80')
    # get_model_textures('0022ED80')
    get_model_textures('86BFFE80')
