"""
ECB没有偏移量
"""
from Cryptodome.Cipher import AES
from binascii import b2a_hex, a2b_hex
import base64



def add_to_16(text):
    if len(text.encode('utf-8')) % 16:
        add = 16 - (len(text.encode('utf-8')) % 16)
    else:
        add = 0
    text = text + ('\0' * add)
    return text.encode('utf-8')


# 加密函数
def encrypt(text, key="123456789abcdefg"):
    key = key.encode('utf-8')
    mode = AES.MODE_ECB
    text = base64.b64encode(text.encode("utf-8")).decode('utf-8')
    text = add_to_16(text)
    cryptos = AES.new(key, mode)

    cipher_text = cryptos.encrypt(text)
    return b2a_hex(cipher_text).decode('utf-8')


# 解密后，去掉补足的空格用strip() 去掉
def decrypt(text, key="123456789abcdefg"):
    key = key.encode('utf-8')
    mode = AES.MODE_ECB
    cryptor = AES.new(key, mode)
    plain_text = cryptor.decrypt(a2b_hex(text))
    rlt = bytes.decode(plain_text).rstrip('\0')
    return base64.b64decode(rlt).decode('utf-8')


if __name__ == '__main__':
    e = encrypt("hello world", "123456789abcdefg")  # 加密
    d = decrypt(e, "123456789abcdefg")  # 解密
    print("加密:", e)
    print("解密:", d)