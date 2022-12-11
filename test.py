# import socket

# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# sock.settimeout(2)
# sock.connect(("59.127.95.47", 27019))

# # sock.send(b"\xff\xff\xff\xffTSource Engine Query\x00\x0a\x08\x5e\xea")
# sock.send(b"\xff\xff\xff\xffU\xff\xff\xff\xff")
# print(sock.recv(65565))

from modules import C_Formatter
from logging import getLogger, StreamHandler

handler = StreamHandler()
handler.setFormatter(C_Formatter())
logger = getLogger("main")
logger.addHandler(handler)

logger.warning("123 %s", "456")
