import socket
import threading
import os
import urllib.parse
import html


class HTTPServer:
    def __init__(self, host='0.0.0.0', port=3000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.request_history = []

    def create_server_socket(self):
        """Создание и настройка основного сокета"""
        try:
            # Создаем сокет TCP
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Разрешаем повторное использование адреса
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Связываем сокет с адресом и портом
            self.server_socket.bind((self.host, self.port))

            # Переводим сокет в режим прослушивания
            self.server_socket.listen(5)

            print(f"Сервер запущен на {self.host}:{self.port}")
        except Exception as e:
            print(f"Ошибка при создании сокета: {e}")
            exit(1)

    def handle_client(self, client_socket, client_address):
        """Обработка запроса от клиента в отдельном потоке"""
        try:
            # Получаем HTTP-запрос
            request = client_socket.recv(1024).decode('utf-8')

            # Вывод полученного запроса
            print(f"\nПолученный запрос от {client_address}:")
            print(request)

            # Парсинг первой строки запроса
            try:
                request_line = request.split('\n')[0].strip()
                method, path, protocol = request_line.split()
                # Декодирование URL
                path = urllib.parse.unquote(path)
            except ValueError:
                # Если не удалось распарсить запрос
                response = (
                    "HTTP/1.1 400 Bad Request\r\n"
                    "Content-Type: text/plain\r\n\r\n"
                    "Неверный формат запроса"
                )
                client_socket.sendall(response.encode('utf-8'))
                self.add_to_request_history(request, response)
                return

            # Обработка favicon.ico
            if path == '/favicon.ico':
                response = (
                    "HTTP/1.1 404 Not Found\r\n"
                    "Content-Type: text/plain; charset=utf-8\r\n\r\n"
                    "Favicon not found"
                )
                client_socket.sendall(response.encode('utf-8'))
                return

            # Формирование ответа
            if method == 'GET':
                if path == '/':
                    # Создаем HTML-страницу группы с отчетами
                    response_body = self.create_group_page()
                    response = (
                        f"HTTP/1.1 200 OK\r\n"
                        f"Server: ПМИМ-31 Web Server\r\n"
                        f"Content-Type: text/html; charset=utf-8\r\n"
                        f"Content-Length: {len(response_body)}\r\n\r\n"
                        f"{response_body}"
                    )
                elif path.startswith('/static/reports/'):
                    # Обработка запросов к PDF-файлам
                    response_body = self.serve_pdf(path)
                    if response_body:
                        response = (
                            f"HTTP/1.1 200 OK\r\n"
                            f"Content-Type: application/pdf\r\n"
                            f"Content-Length: {len(response_body)}\r\n\r\n"
                        )
                        client_socket.sendall(response.encode('utf-8'))
                        client_socket.sendall(response_body)
                        self.add_to_request_history(request, "PDF file sent")
                        client_socket.close()
                        return
                    else:
                        response = (
                            "HTTP/1.1 404 Not Found\r\n"
                            "Content-Type: text/plain; charset=utf-8\r\n\r\n"
                            "Файл не найден"
                        )

            else:
                # Обработка неподдерживаемых методов
                response = (
                    "HTTP/1.1 405 Method Not Allowed\r\n"
                    "Content-Type: text/plain\r\n\r\n"
                    "Метод не поддерживается"
                )

            # Вывод сформированного ответа
            print("\nОтправляемый ответ:")
            print(response)

            # Сохраняем информацию о запросе и ответе
            self.add_to_request_history(request, response)

            # Отправка ответа клиенту
            client_socket.sendall(response.encode('utf-8'))

        except Exception as e:
            print(f"Ошибка при обработке запроса: {e}")

        finally:
            # Закрытие клиентского сокета
            if not client_socket._closed:
                client_socket.close()

    def add_to_request_history(self, request, response):
        # Усечение длинных запросов/ответов
        request_str = str(request)  # Максимум 1000 символов
        response_str = str(response)

        # Ограничиваем историю 50 последними записями
        if len(self.request_history) >= 50:
            self.request_history.pop(0)

        # Добавляем запись в историю
        self.request_history.append({
            'request': request_str,
            'response': response_str
        })

        # Отладочная печать
        print(f"DEBUG: Добавлена запись в историю. Размер: {len(self.request_history)}")

    def serve_pdf(self, path):
        """Чтение и возврат содержимого PDF-файла"""
        try:
            full_path = os.path.join(self.base_dir, path.lstrip('/'))
            with open(full_path, 'rb') as file:
                return file.read()
        except FileNotFoundError:
            print(f"PDF файл не найден: {full_path}")
            return None

    def list_reports(self):
        """Получение списка отчетов"""
        reports_path = os.path.join(self.base_dir, 'static', 'reports')
        try:
            reports = sorted(os.listdir(reports_path))
            return [report for report in reports if report.endswith('.pdf')]
        except FileNotFoundError:
            return []

    def create_group_page(self):
        reports = self.list_reports()
        print("DEBUG: reports =", reports)
        reports_html = ''.join([
            f'<li><a href="/static/reports/{report}">{report}</a></li>'
            for report in reports
        ])
        print("DEBUG: reports_html =", reports_html)

        # Проверьте длину HTML-контента
        print("DEBUG: HTML length =", len(reports_html))

        # Создание HTML для истории запросов
        requests_history_html = ''.join([
            f'''
                <div class="request-response">
                    <div class="request">
                        <h3>Запрос:</h3>
                        <pre>{html.escape(record['request'])}</pre>
                    </div>
                    <div class="response">
                        <h3>Ответ:</h3>
                        <pre>{html.escape(record['response'])}</pre>
                    </div>
                </div>
                '''
            for record in reversed(self.request_history)
        ])

        return f"""
                <!DOCTYPE html>
                <html lang="ru">
                <head>
                    <meta charset="UTF-8">
                    <title>Группа ПМИМ-31</title>
                    <style>
                        body {{ 
                            font-family: Arial, sans-serif; 
                            max-width: 1200px; 
                            margin: 0 auto; 
                            padding: 20px; 
                            line-height: 1.6; 
                        }}
                        h1, h2 {{ color: #333; text-align: center; }}
                        .members, .reports, .request-history {{ 
                            background-color: #f4f4f4; 
                            padding: 15px; 
                            border-radius: 5px;
                            margin-bottom: 20px; 
                        }}
                        a {{ color: #0066cc; text-decoration: none; }}
                        a:hover {{ text-decoration: underline; }}
                        .request-response {{
                            border: 1px solid #ddd;
                            margin-bottom: 10px;
                            padding: 10px;
                        }}
                        pre {{
                            background-color: #e9e9e9;
                            padding: 10px;
                            border-radius: 5px;
                            white-space: pre-wrap;
                            word-wrap: break-word;
                            font-size: 0.8em;
                        }}
                    </style>
                </head>
                <body>
                    <h1>Группа ПМИМ-31</h1>
                    <div class="members">
                        <h2>Состав бригады:</h2>
                        <ul>
                            <li>Тарулин М.А.</li>
                            <li>Холодова В.С.</li>
                        </ul>
                    </div>
                    <div class="reports">
                        <h2>Отчеты:</h2>
                        <ul>
                            {reports_html}
                        </ul>
                    </div>
                    <div class="request-history">
                        <h2>История запросов и ответов:</h2>
                        {requests_history_html}
                    </div>
                </body>
                </html>
                """

    def start(self):
        """Основной цикл сервера"""
        # Создание серверного сокета
        self.create_server_socket()

        try:
            while True:
                # Ожидание подключения
                client_socket, client_address = self.server_socket.accept()
                print(f"\nПодключение от {client_address}")

                # Создание нового потока для обработки клиента
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.start()

        except KeyboardInterrupt:
            print("\nСервер остановлен.")

        finally:
            # Закрытие серверного сокета
            if self.server_socket:
                self.server_socket.close()


# Запуск сервера
if __name__ == "__main__":
    server = HTTPServer(host='0.0.0.0', port=3000)
    server.list_reports()
    server.start()

