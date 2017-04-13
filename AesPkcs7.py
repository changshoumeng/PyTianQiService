# coding: utf8
from Crypto.Cipher import AES
# from binascii import b2a_hex, a2b_hex
# import base64


def printMemLog2(mem):
    byteData = bytearray(mem)
    byteLen = len(byteData)
    print "printMemLog begin .......byteLen:{0}".format(byteLen)
    i = 0
    while i <= byteLen - 1:
        a = byteData[i]
        if i == byteLen - 1:
            print "%02x " % (a)
            break;

        i += 1
        b = byteData[i]
        print "%02x%02x " % (a, b),
        i += 1

        if i % 64 == 0:
            print
    print
    print "*" * 10
    pass


# 将text按照byteAlignLen字节对齐，如果不对齐，按照差数填充
def bytePad(text, byteAlignLen=16):
    count = len(text)
    mod_num = count % byteAlignLen
    if mod_num == 0:
        return text
    add_num = byteAlignLen - mod_num
    print "bytePad:", add_num
    return text + chr(add_num) * add_num


def bytePad2(text, byteAlignLen=16):
    count = len(text)
    mod_num = count % byteAlignLen
    if mod_num == 0:
        #print "bytepad11111:", byteAlignLen
        return text + chr(byteAlignLen) * byteAlignLen
    add_num = byteAlignLen - mod_num
    #print "bytePad:", add_num
    return text + chr(add_num) * add_num


def byteUnpad(text, byteAlignLen=16):
    # printMemLog2(text)
    count = len(text)
    #print "byteUnpad count:", count
    mod_num = count % byteAlignLen
    assert mod_num == 0
    lastChar = text[-1]
    lastLen = ord(lastChar)
    #print "byteUnpad lastLen:", lastLen
    lastChunk = text[-lastLen:]
    lastChunk2 = chr(lastLen) * lastLen
    #print "lastChunk:", len(lastChunk2)
    if len(lastChunk) == len(lastChunk2) and (lastChunk == lastChunk2):
        #print "need unpad"
        return text[:-lastLen]
    #print "no need  unpad"
    return text


class prpcrypt():
    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_ECB
        self.iv = '\0' * 16

    # 加密函数，如果text不是16的倍数【加密文本text必须为16的倍数！】，那就补足为16的倍数
    def encrypt(self, text):
        cryptor = AES.new(self.key, self.mode)
        # 这里密钥key 长度必须为16（AES-128）、24（AES-192）、或32（AES-256）Bytes 长度.目前AES-128足够用
        # length = 16
        text = bytePad2(text, 16)
        # add = length - (count % length)
        # text = text + ('\0' * add)

        self.ciphertext = cryptor.encrypt(text)
        # 因为AES加密时候得到的字符串不一定是ascii字符集的，输出到终端或者保存时候可能存在问题
        # 所以这里统一把加密后的字符串转化为16进制字符串
        return self.ciphertext
        # return b2a_hex(self.ciphertext)

    # 解密后，去掉补足的空格用strip() 去掉
    def decrypt(self, text):
        cryptor = AES.new(self.key, self.mode)
        # plain_text = cryptor.decrypt(a2b_hex(text))
        plain_text = cryptor.decrypt(text)
        # return plain_text
        # printMemLog2(plain_text)
        # print plain_text
        return byteUnpad(plain_text, 16)


