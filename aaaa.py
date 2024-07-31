def extract_uid(hex_value):
    # Remove o prefixo '0x' se existir
    if hex_value.startswith('0x'):
        hex_value = hex_value[2:]

    # Ignora os primeiros 8 caracteres (4 bytes)
    relevant_part = hex_value[8:]

    # Extrai os primeiros 14 caracteres após o prefixo
    uid_hex = relevant_part[:14]

    # Converte a string hexadecimal em bytes
    uid_bytes = bytes.fromhex(uid_hex)

    # Formata os bytes como um UID
    uid = ':'.join(f'{byte:02X}' for byte in uid_bytes)
    return uid

# Valores lidos das tags
hex_value1 = '0xE28068940000502B39329C43'
hex_value2 = '0xE28068940000502B39322843'
#04:14:4C:0A:2A:19:91
#04:76:4B:0A:2A:19:91

# UIDs reais extraídos
uid1 = extract_uid(hex_value1)
uid2 = extract_uid(hex_value2)

print(f'UID real para {hex_value1}: {uid1}')
print(f'UID real para {hex_value2}: {uid2}')
