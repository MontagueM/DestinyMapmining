package_name = "0369-00000B2F"


def hash_pkg(package):
    pkg = package.replace(".bin", "")

    firsthex_int = int(pkg[:4], 16)
    secondhex_int = int(pkg[5:], 16)

    one = firsthex_int*8192
    two = hex(one + secondhex_int + 2155872256)
    return two[2:]


print(hash_pkg(package_name).upper())
