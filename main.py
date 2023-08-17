from dotenv import load_dotenv, set_key
from os import getenv
from requests import get
from json import loads as json_loads
from time import sleep
from bs4 import BeautifulSoup

DOT_ENV_API_KEY_NAME = "TG_API_KEY"
DOT_ENV_GROUP_ID_NAME = "GROUP_ID"
GROUP_ID_CHECK_TIMEOUT = 5
PARSE_TIMEOUT = 10
WOIDEN_URL = "https://woiden.id/create-vps/"
HAX_URL = "https://hax.co.id/create-vps/"


class App:
    def __init__(self,
                 api_key: str = "None",
                 group_id: str = "None",
                 parse_hax: bool = True,
                 parse_woiden: bool = True) -> None:
        load_dotenv()
        self.parse_hax = parse_hax
        self.parse_woiden = parse_woiden

        # Api key and group id were specified when calling class
        if api_key != "None" and group_id != "None":
            self.parse(api_key, group_id)

        # Api key and group id were saved in dotenv
        elif self.check_if_api_key_saved() and self.check_if_group_id_saved():
            print("API key and group id were obtained from .env")
            env_api_key = getenv(DOT_ENV_API_KEY_NAME)
            env_group_id = getenv(DOT_ENV_GROUP_ID_NAME)
            self.parse(env_api_key, env_group_id)

        # Creating API key and getting group id
        else:
            self.bot_creation()

    @staticmethod
    def check_if_api_key_saved() -> bool:
        if getenv(DOT_ENV_API_KEY_NAME) is None:
            # Api key isn't saved
            return False
        else:
            # Api key saved
            return True

    @staticmethod
    def check_if_group_id_saved() -> bool:
        if getenv(DOT_ENV_GROUP_ID_NAME) is None:
            # Group ID isn't saved
            return False
        else:
            # Group ID saved
            return True

    def bot_creation(self) -> None:
        """Shows bot creation guide. Gets API key and then gets group id"""

        print("There isn't API key and group id in .env")
        print("You need to create bot in Telegram via @BotFather. Then enter API key below")
        print("Check README.md for more advanced guide.")
        api_key = input("> ")
        print("Now you need to create group and add bot to that group as admin.")
        print(f"Script will check it every {GROUP_ID_CHECK_TIMEOUT} seconds.")

        # It gets all bot updates. When it detects that bot was added as admin to group it will save API and group id
        # in .env file. After that you no longer need to enter API key.
        while True:
            data = json_loads(get(f"https://api.telegram.org/bot{api_key}/getUpdates").text)
            if data['ok']:
                result = data.get('result')
                if len(result) != 0:
                    try:
                        # Gets bot status
                        status = result[-1]['my_chat_member']['new_chat_member']['status']

                        if status == 'administrator':
                            print("Bot added.")
                            # Getting group id
                            group_id = str(result[-1]['my_chat_member']['chat']['id'])

                            # Saving API key and group id
                            set_key('.env', DOT_ENV_API_KEY_NAME, api_key)
                            set_key('.env', DOT_ENV_GROUP_ID_NAME, group_id)

                            load_dotenv()
                            env_api_key = getenv(DOT_ENV_API_KEY_NAME)
                            env_group_id = getenv(DOT_ENV_GROUP_ID_NAME)
                            self.parse(env_api_key, env_group_id)

                            break

                        elif status == "member":
                            print("Bot is member. You need to grant him admin rights.")

                    except KeyError:
                        pass
            else:
                print("Error:", data['error_code'])
                print("Raw:", data)

            sleep(GROUP_ID_CHECK_TIMEOUT)

    def parse(self, api_key: str, group_id: str) -> None:
        """Parses page from woiden/hax then gets list of available servers. If there is available servers it will
        send notification in telegram chat. """

        def _get_available_datacenters(html_data: BeautifulSoup) -> list:
            """Returns list of datacenters (including -select-)"""
            datacenters = list()
            for i in html_data.select("form[id='form-submit'] > .form-group > select[id='datacenter'] > option"):
                datacenters.append(i.text)
            return datacenters

        def datacenters_handler(datacenters: list, hosting_url: str) -> bool:
            """If there is available datacenters it will send message in telegram group (without -select-) then it will
            return True.
            True - message was sent. Stop parsing.
            False - There isn't available datacenters. Continue parsing."""
            if len(datacenters) == 1 and datacenters[0] == '-select-':
                print(hosting_url, "No datacenters available.")
                return False
            else:
                dc_list = "".join([i+"\n" for i in datacenters[1:]])

                get(f"https://api.telegram.org/"
                    f"bot{api_key}/"
                    f"sendMessage?"
                    f"chat_id={group_id}&"
                    f"text=There are available servers at {hosting_url}\n"
                    f"Servers:\n"
                    f"{dc_list}")
                return True

        while True:
            print('='*32)
            if self.parse_hax:
                data = get(HAX_URL)
                hax_html = BeautifulSoup(data.content, 'html.parser')
                hax_dc = _get_available_datacenters(hax_html)
                # If handler returns True it will stop parsing
                if datacenters_handler(hax_dc, 'https://hax.co.id'):
                    self.parse_hax = False
                    print("https://hax.co.id Servers available. Message sent!")

            if self.parse_woiden:
                data = get(WOIDEN_URL)
                woiden_html = BeautifulSoup(data.content, 'html.parser')
                woiden_dc = _get_available_datacenters(woiden_html)
                # If handler returns True it will stop parsing
                if datacenters_handler(woiden_dc, 'https://woiden.id'):
                    self.parse_woiden = False
                    print("https://woiden.id Servers available. Message sent!")

            if not self.parse_woiden and not self.parse_hax:
                break

            sleep(PARSE_TIMEOUT)
        print('='*32)


if __name__ == "__main__":
    try:
        App()
    except KeyboardInterrupt:
        print("Exiting...")
        exit()
