import logging
import os
import requests

from dotenv import load_dotenv
from random import randint
from requests.exceptions import HTTPError, ConnectionError
from urllib.parse import urlsplit


def get_comic_json(comic_number):
    xkcd_url = 'https://xkcd.com/'
    full_url = os.path.join(f'{xkcd_url}{comic_number}', 'info.0.json')

    response = requests.get(full_url)
    response.raise_for_status()
    return response.json()


def download_image(comic_json):
    comic_link = comic_json['img']
    filename = os.path.split(comic_link)[-1]

    response = requests.get(comic_link)
    response.raise_for_status()

    with open(filename, 'wb') as file:
        file.write(response.content)
    logging.info(f'Downloaded file {filename}')
    raise ValueError
    return filename


def get_upload_link_and_ids():
    method_name = 'photos.getWallUploadServer'
    vk_url = f'https://api.vk.com/method/{method_name}'
    payload = {
        'access_token': ACCESS_TOKEN,
        'v': VK_API_VERSION,
        'group_id': GROUP_ID,
    }
    response = requests.get(vk_url, params=payload)
    response.raise_for_status()
    check_response_for_error(response)
    return response.json()['response']


def get_server_url_and_photos_hash(photo, server):
    photo_filepath = f'./{photo}'
    with open(photo_filepath, 'rb') as file:
        files = {'photo': file}
        response = requests.post(server, files=files)
        response.raise_for_status()
        check_response_for_error(response)
    return response.json()


def save_photo_on_server(comic_json):
    photo_filename = download_image(comic_json)
    upload_url = get_upload_link_and_ids()['upload_url']

    server_answer = get_server_url_and_photos_hash(photo_filename, upload_url)
    payload = {
        'access_token': ACCESS_TOKEN,
        'v': VK_API_VERSION,
        'group_id': GROUP_ID,
        'photo': server_answer['photo'],
        'hash': server_answer['hash'],
        'server': server_answer['server'],
    }
    method_name = 'photos.saveWallPhoto'
    vk_url = f'https://api.vk.com/method/{method_name}'
    response = requests.get(vk_url, params=payload)
    response.raise_for_status()
    check_response_for_error(response)
    logging.info(f'Uploaded photo {photo_filename} to server')
    return response.json()['response']


def post_photo_on_wall():
    try:
        last_comic_number = get_comic_json('')['num']
        comic_to_download_number = randint(1, last_comic_number)
        comic_json = get_comic_json(comic_to_download_number)
        caption = comic_json['alt']

        photo_params = save_photo_on_server(comic_json)
        photo_id = photo_params[0]['id']
        owner_id = photo_params[0]['owner_id']

        method_name = 'wall.post'
        vk_url = f'https://api.vk.com/method/{method_name}'
        payload = {
            'access_token': ACCESS_TOKEN,
            'v': VK_API_VERSION,
            'attachments': f'photo{owner_id}_{photo_id}',
            'owner_id': f'-{GROUP_ID}',
            'message': caption,
            'from_group': 1,
        }
        response = requests.post(vk_url, params=payload)
        response.raise_for_status()
        check_response_for_error(response)
        logging.info('Posted photo on the wall')
    except (HTTPError, ConnectionError) as error:
        logging.exception(error)
    except KeyError as error:
        logging.exception(error)
    finally:
        filepath = os.path.split(urlsplit(comic_json['img']).path)[-1]
        os.remove(filepath)


def check_response_for_error(response):
    answer = response.json()
    if 'error' in answer:
        logging.error(answer['error'])
        raise HTTPError


if __name__ == '__main__':
    load_dotenv()
    logging.basicConfig(
        filename="comics.log",
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filemode='w',
    )

    ACCESS_TOKEN = os.getenv('VK_ACCESS_TOKEN')
    GROUP_ID = os.getenv('GROUP_ID')
    VK_API_VERSION = 5.131

    post_photo_on_wall()
