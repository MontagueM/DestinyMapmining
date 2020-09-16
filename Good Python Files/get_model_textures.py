import gf


def get_model_textures(model_hash):
    file = gf.get_file_from_hash(gf.get_flipped_hex(model_hash, 8))
    pkg = gf.get_pkg_name(file)
    print(f'C:/d2_output/{pkg}/{file}.bin')
    file_hex = gf.get_hex_data(f'C:/d2_output/{pkg}/{file}.bin')


if __name__ == '__main__':
    get_model_textures('CCC7F380')
    get_model_textures('0A34ED80')
    get_model_textures('4922ED80')
    get_model_textures('0022ED80')
    get_model_textures('86BFFE80')