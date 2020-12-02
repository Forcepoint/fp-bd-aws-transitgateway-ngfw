from ipaddress import IPv4Address, ip_network


class MyIPv4(IPv4Address):
    def __and__(self, other: IPv4Address):
        if not isinstance(other, (int, IPv4Address)):
            raise NotImplementedError
        return self.__class__(int(self) & int(other))


def ip_range_calculator(base_address, address):
    if ((base_address + 50) > address) or ((base_address + 50) <= address and (base_address + 100) < address):
        return f'{(base_address + 50)}-{(base_address + 100)}'
    elif (base_address + 100) > address:
        return f'{(base_address + 100)}-{(base_address + 150)}'
    else:
        return f'{(base_address + 150)}-{(base_address + 200)}'


def string_to_ip(base):

    return ip_network(str(base))
