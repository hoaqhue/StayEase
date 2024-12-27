import hashlib
import hmac
import urllib.parse

class Vnpay:
    responseData = {}
    def __init__(self,tmn_code,secret_key,return_url,vnpay_payment_url,api_url):
        self.tmn_code = tmn_code
        self.secret_key = secret_key
        self.return_url= return_url
        self.vnpay_payment_url = vnpay_payment_url
        self.api_url = api_url
    def get_payment_url(self, requestData):
        inputData = sorted(requestData.items())
        queryString = ''
        hasData = ''
        seq = 0
        for key, val in inputData:
            if seq == 1:
                queryString = queryString + "&" + key + '=' + urllib.parse.quote_plus(str(val))
            else:
                seq = 1
                queryString = key + '=' + urllib.parse.quote_plus(str(val))

        hashValue = self.__hmacsha512(self.secret_key, queryString)
        return self.vnpay_payment_url + "?" + queryString + '&vnp_SecureHash=' + hashValue

    def validate_response(self,responseData):
        vnp_SecureHash = responseData['vnp_SecureHash']
        # Remove hash params
        if 'vnp_SecureHash' in responseData.keys():
            responseData.pop('vnp_SecureHash')

        if 'vnp_SecureHashType' in responseData.keys():
            responseData.pop('vnp_SecureHashType')

        inputData = sorted(responseData.items())
        hasData = ''
        seq = 0
        for key, val in inputData:
            if str(key).startswith('vnp_'):
                if seq == 1:
                    hasData = hasData + "&" + str(key) + '=' + urllib.parse.quote_plus(str(val))
                else:
                    seq = 1
                    hasData = str(key) + '=' + urllib.parse.quote_plus(str(val))
        hashValue = self.__hmacsha512(self.secret_key, hasData)

        print(
            'Validate debug, HashData:' + hasData + "\n HashValue:" + hashValue + "\nInputHash:" + vnp_SecureHash)

        return vnp_SecureHash == hashValue

    @staticmethod
    def __hmacsha512(key, data):
        byteKey = key.encode('utf-8')
        byteData = data.encode('utf-8')
        return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()