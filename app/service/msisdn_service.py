import requests

def make_post_request(imsi):
        mcc = imsi[:3]
        mnc = imsi[3:5]
        
        params = {
            "i": imsi,
            "l": '',
            "c": '',
            "cc": mcc,
            "nc": mnc,
            "k": 'CAAA89A74C6A3CDD655CB43F134AC'
        }

        url = "http://157.230.34.151:1442/WmoMpmdGan_trans.php"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(url, headers=headers, data=params)

        json_response = response.json()
        print(f'respon json {json_response}')

        if 'message' in json_response and json_response['message'] == 'Not Found':
            print("Message 'Not Found' received. Setting msisdn to '-'.")
            return '-'
        
        if 'body' in json_response:
            msisdn = json_response['body'].get('msisdn', None)
            print("MSISDN:", msisdn)
            return msisdn
        else:
            print("MSISDN not found in the response.")
            return None

def translate_telkomsel(imsi: str) -> str:
    pre = '628'
    imsi = imsi.strip()
    im1 = imsi[5:]         
    im2 = im1[0:2]         
    im3 = im1[0:4]         
    im4 = im3[2]           
    im5 = im1[4:]          
    mapping = {
        '1': '11',
        '2': '12',
        '3': '13',
        '6': '21',
        '7': '22',
        '8': '23',
        '9': '51',
        '4': '52'
    }
    imm = mapping.get(im4, '53')

    return f"{pre}{imm}{im2}{im5}"
