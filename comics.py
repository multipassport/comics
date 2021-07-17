import logging
import os
import requests
import sys

from dotenv import load_dotenv
from random import randint
from requests.exceptions import HTTPError, ConnectionError
from urllib.parse import urlsplit


def get_xkcd_response(comic_number):
    xkcd_url = 'https://xkcd.com/'
    full_url = os.path.join(f'{xkcd_url}{comic_number}', 'info.0.json')

    response = requests.get(full_url)
    response.raise_for_status()
    return response.json()


def download_image(comic_link):
    comic_filepath = os.path.split(urlsplit(comic_link).path)[-1]

    response = requests.get(comic_link)
    response.raise_for_status()

    with open(comic_filepath, 'wb') as file:
        file.write(response.content)
    logging.info(f'Downloaded file {comic_filepath}')
    return comic_filepath


def get_upload_link_and_ids(access_token, group_id, vk_api_version):
    method_name = 'photos.getWallUploadServer'
    vk_url = f'https://api.vk.com/method/{method_name}'
    payload = {
        'access_token': access_token,
        'v': vk_api_version,
        'group_id': group_id,
    }
    response = requests.get(vk_url, params=payload)
    response.raise_for_status()
    answer = response.json()
    check_response_for_error(answer)
    return answer['response']


def get_server_url_and_photos_hash(photo, server):
    photo_filepath = f'./{photo}'
    with open(photo_filepath, 'rb') as file:
        files = {'photo': file}
        response = requests.post(server, files=files)
    response.raise_for_status()
    answer = response.json()
    check_response_for_error(answer)
    return answer


def save_photo_on_server(
        image,
        image_hash,
        server_id,
        comic_filepath,
        access_token,
        group_id,
        vk_api_version):

    payload = {
        'access_token': access_token,
        'v': vk_api_version,
        'group_id': group_id,
        'photo': image,
        'hash': image_hash,
        'server': server_id,
    }
    method_name = 'photos.saveWallPhoto'
    vk_url = f'https://api.vk.com/method/{method_name}'
    response = requests.get(vk_url, params=payload)
    response.raise_for_status()
    answer = response.json()
    check_response_for_error(answer)
    logging.info(f'Uploaded photo {comic_filepath} to server')
    return answer['response']


def download_random_comic():
    last_comic_number = get_xkcd_response('')['num']
    comic_to_download_number = randint(1, last_comic_number)
    xkcd_response = get_xkcd_response(comic_to_download_number)

    caption = xkcd_response['alt']
    comic_link = xkcd_response['img']
    comic_filepath = download_image(comic_link)
    return comic_filepath, caption


def post_comic_on_wall(access_token, group_id, vk_api_version):
    try:
        comic_filepath, caption = download_random_comic()
    except (HTTPError, ConnectionError) as error:
        logging.exception(error)
        sys.exit(1)

    try:
        upload_url = get_upload_link_and_ids(
            access_token,
            group_id,
            vk_api_version)['upload_url']

        server_answer = get_server_url_and_photos_hash(
            comic_filepath,
            upload_url,
        )
        image_metadata = server_answer['photo']
        image_hash = server_answer['hash']
        server_id = server_answer['server']

        photo_params = save_photo_on_server(
            image_metadata,
            image_hash,
            server_id,
            comic_filepath,
            access_token,
            group_id,
            vk_api_version
        )
        photo_id = photo_params[0]['id']
        owner_id = photo_params[0]['owner_id']

        method_name = 'wall.post'
        vk_url = f'https://api.vk.com/method/{method_name}'
        payload = {
            'access_token': access_token,
            'v': vk_api_version,
            'attachments': f'photo{owner_id}_{photo_id}',
            'owner_id': f'-{group_id}',
            'message': caption,
            'from_group': 1,
        }
        response = requests.post(vk_url, params=payload)
        response.raise_for_status()
        answer = response.json()
        check_response_for_error(answer)
        logging.info('Posted photo on the wall')
    except (HTTPError, ConnectionError, KeyError) as error:
        logging.exception(error)
    finally:
        os.remove(comic_filepath)


def check_response_for_error(answer):
    if 'error' in answer:
        raise HTTPError(answer['error'])


if __name__ == '__main__':
    load_dotenv()
    logging.basicConfig(
        filename='comics.log',
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filemode='w',
    )

    access_token = os.getenv('VK_ACCESS_TOKEN')
    group_id = os.getenv('GROUP_ID')
    vk_api_version = 5.131

    post_comic_on_wall(access_token, group_id, vk_api_version)
