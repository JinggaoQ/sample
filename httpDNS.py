#!/usr/bin/env python
#
# Copyright (c) 2012 OpenDNS, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the OpenDNS nor the names of its contributors may be
#      used to endorse or promote products derived from this software without
#      specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL OPENDNS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

""" Class to implement draft-ietf-dnsop-edns-client-subnet (previously known as
draft-vandergaast-edns-client-subnet.

The contained class supports both IPv4 and IPv6 addresses.
Requirements:
  dnspython (http://www.dnspython.org/)
"""
from __future__ import print_function
from __future__ import division

import socket
import struct
import dns
import dns.edns
import dns.flags
import dns.message
import dns.query
import json


ASSIGNED_OPTION_CODE = 0x0008
DRAFT_OPTION_CODE = 0x50FA

FAMILY_IPV4 = 1
FAMILY_IPV6 = 2
SUPPORTED_FAMILIES = (FAMILY_IPV4, FAMILY_IPV6)


class ClientSubnetOption(dns.edns.Option):
    """Implementation of draft-vandergaast-edns-client-subnet-01.

    Attributes:
        family: An integer inidicating which address family is being sent
        ip: IP address in integer notation
        mask: An integer representing the number of relevant bits being sent
        scope: An integer representing the number of significant bits used by
            the authoritative server.
    """

    def __init__(self, ip, bits=-1, scope=0, option=ASSIGNED_OPTION_CODE):
        super(ClientSubnetOption, self).__init__(option)

        n = None
        f = None

        for family in (socket.AF_INET, socket.AF_INET6):
            try:
                n = socket.inet_pton(family, ip)
                if family == socket.AF_INET6:
                    f = FAMILY_IPV6
                    if bits == -1:
                        bits = 48
                    hi, lo = struct.unpack('!QQ', n)
                    ip = hi << 64 | lo
                elif family == socket.AF_INET:
                    f = FAMILY_IPV4
                    if bits == -1:
                        bits = 24
                    ip = struct.unpack('!L', n)[0]
            except Exception:
                pass

        if n is None:
            raise Exception("%s is an invalid ip" % ip)

        self.family = f
        self.ip = ip
        self.mask = bits
        self.scope = scope
        self.option = option

        if self.family == FAMILY_IPV4 and self.mask > 32:
            raise Exception("32 bits is the max for IPv4 (%d)" % bits)
        if self.family == FAMILY_IPV6 and self.mask > 128:
            raise Exception("128 bits is the max for IPv6 (%d)" % bits)

    def calculate_ip(self):
        """Calculates the relevant ip address based on the network mask.

        Calculates the relevant bits of the IP address based on network mask.
        Sizes up to the nearest octet for use with wire format.

        Returns:
            An integer of only the significant bits sized up to the nearest
            octect.
        """

        if self.family == FAMILY_IPV4:
            bits = 32
        elif self.family == FAMILY_IPV6:
            bits = 128

        ip = self.ip >> bits - self.mask

        if (self.mask % 8 != 0):
            ip = ip << 8 - (self.mask % 8)

        return ip

    def is_draft(self):
        """" Determines whether this instance is using the draft option code """
        return self.option == DRAFT_OPTION_CODE

    def to_wire(self, file):
        """Create EDNS packet as definied in draft-vandergaast-edns-client-subnet-01."""

        ip = self.calculate_ip()

        mask_bits = self.mask
        if mask_bits % 8 != 0:
                mask_bits += 8 - (self.mask % 8)

        if self.family == FAMILY_IPV4:
            test = struct.pack("!L", ip)
        elif self.family == FAMILY_IPV6:
            test = struct.pack("!QQ", ip >> 64, ip & (2 ** 64 - 1))
        test = test[-(mask_bits // 8):]

        format = "!HBB%ds" % (mask_bits // 8)
        data = struct.pack(format, self.family, self.mask, self.scope, test)
        file.write(data)

    def from_wire(cls, otype, wire, current, olen):
        """Read EDNS packet as defined in draft-vandergaast-edns-client-subnet-01.

        Returns:
            An instance of ClientSubnetOption based on the ENDS packet
        """

        data = wire[current:current + olen]
        (family, mask, scope) = struct.unpack("!HBB", data[:4])

        c_mask = mask
        if mask % 8 != 0:
            c_mask += 8 - (mask % 8)

        ip = struct.unpack_from("!%ds" % (c_mask // 8), data, 4)[0]

        if (family == FAMILY_IPV4):
            ip = ip + b'\0' * ((32 - c_mask) // 8)
            ip = socket.inet_ntop(socket.AF_INET, ip)
        elif (family == FAMILY_IPV6):
            ip = ip + b'\0' * ((128 - c_mask) // 8)
            ip = socket.inet_ntop(socket.AF_INET6, ip)
        else:
            raise Exception("Returned a family other then IPv4 or IPv6")

        return cls(ip, mask, scope, otype)

    from_wire = classmethod(from_wire)

    def __repr__(self):
        if self.family == FAMILY_IPV4:
            ip = socket.inet_ntop(socket.AF_INET, struct.pack('!L', self.ip))
        elif self.family == FAMILY_IPV6:
            ip = socket.inet_ntop(socket.AF_INET6,
                                  struct.pack('!QQ',
                                              self.ip >> 64,
                                              self.ip & (2 ** 64 - 1)))

        return "%s(%s, %s, %s)" % (
            self.__class__.__name__,
            ip,
            self.mask,
            self.scope
        )

    def __eq__(self, other):
        """Rich comparison method for equality.

        Two ClientSubnetOptions are equal if their relevant ip bits, mask, and
        family are identical. We ignore scope since generally we want to
        compare questions to responses and that bit is only relevant when
        determining caching behavior.

        Returns:
            boolean
        """

        if not isinstance(other, ClientSubnetOption):
            return False
        if self.calculate_ip() != other.calculate_ip():
            return False
        if self.mask != other.mask:
            return False
        if self.family != other.family:
            return False
        return True

    def __ne__(self, other):
        """Rich comparison method for inequality.

        See notes for __eq__()

        Returns:
            boolean
        """
        return not self.__eq__(other)


dns.edns._type_to_class[DRAFT_OPTION_CODE] = ClientSubnetOption
dns.edns._type_to_class[ASSIGNED_OPTION_CODE] = ClientSubnetOption


def getDnsResult(recordName, recordType, clientIP):
    resolverIP = '8.8.8.8'
    addr = socket.gethostbyname(resolverIP)
    mask = 24
    option_code=ASSIGNED_OPTION_CODE
    print("Testing for edns-clientsubnet using option code", hex(option_code))
    cso = ClientSubnetOption(clientIP, mask, option_code)
    message = dns.message.make_query(recordName, recordType)
    message.use_edns(options=[cso])
    #message.flags = message.flags | dns.flags.RD
    
    print("message:")
    print(message)
    print("addr")
    print(addr)
    
    r = dns.query.udp(message, addr, timeout=10)
    
    print("query result")
    print(r)
    
    error = False
    found = False
    recordData=""
    for options in r.options:
        # Have not run into anyone who passes back both codes yet
        # but just in case, we want to check all possible options
        if isinstance(options, ClientSubnetOption):
            found = True
            print("Found ClientSubnetOption...")
            if not cso.family == options.family:
                error = True
                print("\nFailed: returned family (%d) is different from the passed family (%d)" % (options.family, cso.family))
            if not cso.calculate_ip() == options.calculate_ip():
                error = True
                print("\nFailed: returned ip (%s) is different from the passed ip (%s)." % (options.calculate_ip(), cso.calculate_ip()))
            if not options.mask == cso.mask:
                error = True
                print("\nFailed: returned mask bits (%d) is different from the passed mask bits (%d)" % (options.mask, cso.mask))
            if not options.scope != 0:
                print("\nWarning: scope indicates edns-clientsubnet data is not used")
            if options.is_draft():
                print("\nWarning: detected support for edns-clientsubnet draft code")

        if found and not error:
            print("Success")
            print(r)
            for rdata in r.answer:
                print(rdata.to_text())
                recordData = rdata.to_text()
        elif found:
            print("Failed: See error messages above")
        else:
            print("Failed: No ClientSubnetOption returned")
    
    return recordData

def lambda_handler(event, context):
    print(event)
    body = json.loads(event['body'])
    recordName = body['recordName']
    recordType = body['recordType']
    clientIP = body['clientIP']
    #recordName = event['recordName']
    #recordType = event['recordType']
    #clientIP = event['clientIP']
    recordData = getDnsResult(recordName,recordType,clientIP)
    
    return {
        "statusCode": 200,
        "statusDescription": "200 OK",
        "isBase64Encoded": False,
        "headers": {
            "Content-Type": "text/html"
        },
        "body": json.dumps(recordData)
    }
