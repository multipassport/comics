import os
import requests


def get_comic_json():
    xkcd_url = 'https://xkcd.com/'
    comic_number = 353
    full_url = os.path.join(f'{xkcd_url}{comic_number}', 'info.0.json')

    response = requests.get(full_url)
    response.raise_for_status()
    return response.json()


def download_image(comic_json):
    comic_link = comic_json['img']
    print(comic_link)
    filename = os.path.split(comic_link)[-1]

    response = requests.get(comic_link)
    response.raise_for_status()

    with open(filename, 'wb') as file:
        file.write(response.content)


if __name__ == '__main__':
    comic_json = get_comic_json()
    download_image(comic_json)
