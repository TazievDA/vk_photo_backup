from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from datetime import datetime
import requests
import os
import json


class VK:
    def __init__(self, access_token, user_id, version='5.154'):
        self.token = access_token
        self.id = user_id
        self.params = {'access_token': self.token, 'v': version}

    # Для проверки изменения названия выгружаем 8 фотографий, так как на 8-й фотографии одинаковое количество лайков.

    def __download_photos(self):
        base_url = 'https://api.vk.com/method/'
        album_input = int(input('Выберите раздел, где необходимо скачать фотографии:'
                                '\n1 — фотографии со стены;\n2 — фотографии профиля.\n'))
        if album_input == 1:
            album = 'wall'
        elif album_input == 2:
            album = 'profile'
        else:
            return 'Неверный ввод.'
        params = {
            'owner_id': self.id
            'extended': 1,
            'count': 8,
            'album_id': album,
            'photo_sizes': 1
        }
        response = requests.get(f'{base_url}photos.get', params={**self.params, **params})
        data = response.json()
        print(f'К загрузке готовы {len(data.get("response", {}).get("items"))} файла(ов)')
        print()
        return data.get('response', {}).get('items')

    # Выгружаем фотографии только максимально возможного качества.
    def __photos_separation(self):
        photos_info = {}
        items = self.__download_photos()
        for item in items:
            for size in item.get('sizes')[::-1]:
                if size.get('type') == 'z' or size.get('type') == 'y' or size.get('type') == 'x' and item.get('id') not in photos_info:
                    photos_info[item.get('id')] = {'url': size.get('url'), 'size': size.get('type'),
                                                   'likes': item.get('likes', {}).get('count'),
                                                   'date': item.get('date')}
        return photos_info

    # Сохраняем фотографии на ПК.
    def save_photo(self):
        data = self.__photos_separation()
        used_names = []
        file_info = []
        for item in data:
            url = data[item]['url']
            date_timestamp = data[item]['date']
            full_date = str(datetime.fromtimestamp(date_timestamp))
            date_for_name = full_date.split(' ')[0]
            likes_count = data[item]['likes']
            size = data[item]['size']
            response = requests.get(url)
            if not os.path.exists('photos'):
                os.makedirs('photos')
            if likes_count not in used_names:
                name = f'photos/{likes_count}.jpeg'
                if not os.path.exists(name):
                    with open(name, 'wb') as file:
                        file.write(response.content)
                    used_names.append(likes_count)
                    info_dict = {"file_name": name.split('/')[1], "size": size}
                    file_info.append(info_dict)
                    print(f'Создан файл с именем {name}')
                else:
                    print(f'Файл {name} уже был сохранён.')
            else:
                name = f'photos/{likes_count}_{date_for_name}.jpeg'
                with open(name, 'wb') as file:
                    file.write(response.content)
                info_dict = {"file_name": name.split('/')[1], "size": size}
                file_info.append(info_dict)
                print(f'Создан файл с именем {name}')
        return file_info


class YD:
    def __init__(self, token):
        self.token = token
        self.headers = {'Authorization': f'OAuth {self.token}'}
        self.baseurl = 'https://cloud-api.yandex.net/v1/disk/resources'

    def save_json(self):
        data = vk.save_photo()
        with open('data.json', 'w') as file:
            json.dump(data, file)
        print()
        print('Файл data.json сохранён в корневую папку проекта.')
        print()

    def create_folder(self):
        current_date = datetime.now().strftime('%d-%m-%Y')
        path = f'VK Photos backup {current_date}'
        params = {'path': path}
        folder = requests.get(f'{self.baseurl}', params=params, headers=self.headers)
        if folder.status_code == 404:
            response = requests.put(f'{self.baseurl}', params=params, headers=self.headers)
        return params

    def get_link_for_upload(self):
        self.save_json()
        data = self.create_folder()
        path = data['path']
        print(f'В Яндекс.Диск создана папка с именем {path}')
        links = []
        for filename in os.listdir('photos'):
            path = f'{data["path"]}/{filename}'
            params = {'path': path}
            try:
                response = requests.get(f'{self.baseurl}/upload', params=params, headers=self.headers)
                links.append(response.json()['href'])
            except Exception as _ex:
                print(f'Файл {filename} уже загружен в папку')
                continue
            print(f'Ссылка для загрузки файла {filename} — {response.json()["href"]}')
        return links

    def upload_photos(self):
        links = self.get_link_for_upload()
        filenames = os.listdir('photos')
        for link, filename in zip(links, filenames):
            file = os.path.join(os.getcwd(), 'photos', filename)
            print(f'Начинаем загрузку файла {filename} в Яндекс.Диск.')
            with open(file, 'rb') as f:
                response = requests.put(link, files={'file': f})
            if response.status_code == 201:
                print(f'Статус загрузки файла {filename}:'
                      f' {response.status_code} — успешно загружено.')
            elif response.status_code == 202:
                print(
                    f'Статус загрузки файла {filename}:'
                    f' {response.status_code} — файл принят сервером, но еще не был перенесен непосредственно '
                    f'в Яндекс.Диск.')
            elif response.status_code == 412:
                print(
                    f'Статус загрузки файла {filename}:'
                    f' {response.status_code} — при дозагрузке файла был передан неверный диапазон '
                    f'в заголовке Content-Range')
            elif response.status_code == 413:
                print(
                    f'Статус загрузки файла {filename}:'
                    f' {response.status_code} — размер файла больше допустимого.')
            elif response.status_code == 500:
                print(
                    f'Статус загрузки файла {filename}:'
                    f' {response.status_code} —  ошибка сервера, попробуйте повторить загрузку.')
            elif response.status_code == 507:
                print(
                    f'Статус загрузки файла {filename}:'
                    f' {response.status_code} —  для загрузки файла не хватает места на Диске пользователя.')


class Google_Drive:
    def __init__(self, folder_id):
        self.gauth = GoogleAuth()
        self.gauth.LocalWebserverAuth()
        self.drive = GoogleDrive(self.gauth)
        self.folder_id = folder_id

    def create_folder(self):
        print()
        data = yd.create_folder()
        foldername = data['path']
        file_metadata = {
            'title': foldername,
            'parents': [{'id': self.folder_id}],
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = self.drive.CreateFile(file_metadata)
        folder.Upload()
        print(f'В Google Drive создана папка с названием {foldername}.')
        print()
        return foldername

    def upload_file(self):
        foldername = self.create_folder()
        folders = self.drive.ListFile({
            'q': "title='" + foldername + "' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        }).GetList()
        filenames = os.listdir('photos')
        for filename in filenames:
            for folder in folders:
                if folder['title'] == foldername:
                    try:
                        file = os.path.join(os.getcwd(), 'photos', filename)
                        print(f'Начинаем загрузку файла {filename} в Google Drive.')
                        with open(file, 'rb') as f:
                            f = self.drive.CreateFile(
                                {'title': filename, 'mimeType': 'image/jpeg', 'parents': [{'id': folder['id']}]})
                            f.SetContentFile(file)
                            f.Upload()
                        print(f'Файл {filename} загружен в Google Drive.')
                    except Exception as _ex:
                        print('Произошла ошибка.')


vk_access_token = 'vk_token'
vk_user_id = input('Введите ID пользователя ВКонтакте: ')

yd_token = 'yd_token'

yd = YD(yd_token)
vk = VK(vk_access_token, vk_user_id)

yd.upload_photos()
gdrive = Google_Drive('root')

gdrive.upload_file()
