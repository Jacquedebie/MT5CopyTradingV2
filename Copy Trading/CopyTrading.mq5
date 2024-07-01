#include <JAson.mqh>

string Address = "127.0.0.1";
int Port = 9094;
bool ExtTLS = false;
int socket = INVALID_HANDLE;

bool HTTPSend(int socket, string request)
{
    char req[];
    int len = StringToCharArray(request, req) - 1;
    Print("Sending request: ", request);  // Debug print

    return (len >= 0) && ((ExtTLS ? SocketTlsSend(socket, req, len) : SocketSend(socket, req, len)) == len);
}

bool HTTPRecv(int socket, uint timeout)
{
    char rsp[2000];
    string buffer = "";
    uint timeout_check = GetTickCount() + timeout;

    while (GetTickCount() < timeout_check && !IsStopped())
    {
        int len = SocketIsReadable(socket);

        if (len > 0)
        {
            int rsp_len = ExtTLS ? SocketTlsRead(socket, rsp, len) : SocketRead(socket, rsp, len, timeout);

            if (rsp_len > 0)
            {
                string partial_result = CharArrayToString(rsp, 0, rsp_len);
                buffer += partial_result;

                Print("Received message: ", partial_result);  // Print each received part

                while (true)
                {
                    int start_pos = StringFind(buffer, "{");
                    int end_pos = StringFind(buffer, "}");

                    if (start_pos != -1 && end_pos != -1 && end_pos > start_pos)
                    {
                        string complete_json = StringSubstr(buffer, start_pos, end_pos - start_pos + 1);
                        Print("Complete JSON: ", complete_json);

                        buffer = StringSubstr(buffer, end_pos + 1);
                    }
                    else
                    {
                        break;
                    }
                }
            }
            else if (rsp_len == -1)
            {
                Print("Socket read error: ", GetLastError());
                return false;
            }
        }

        Sleep(10);
    }

    Print("Final buffer: ", buffer);  

    return StringLen(buffer) > 0;
}

void SendAccountID()
{
    if (socket != INVALID_HANDLE)
    {
        int account_id = AccountInfoInteger(ACCOUNT_LOGIN);
        string message = "{\"Code\":\"Authenticate\",\"account_id\":" + IntegerToString(account_id) + "}";

        bool sent = HTTPSend(socket, message);
        Print("Message sent: ", sent); 
    }
}

void ConnectToServer()
{
    socket = SocketCreate();

    if (socket != INVALID_HANDLE && SocketConnect(socket, Address, Port, 1000))
    {
        Print("Connected to ", Address, ":", Port);

        string subject, issuer, serial, thumbprint;
        datetime expiration;

        if (SocketTlsCertificate(socket, subject, issuer, serial, thumbprint, expiration))
        {
            Print("TLS certificate:\nOwner: ", subject, "\nIssuer: ", issuer, "\nNumber: ", serial, "\nPrint: ", thumbprint, "\nExpiration: ", expiration);
            ExtTLS = true;
        }

        SendAccountID(); 
    }
    else
    {
        Print("Connection to ", Address, ":", Port, " failed, error ", GetLastError());
        SocketClose(socket);
        socket = INVALID_HANDLE;
    }
}

void OnInit()
{
    ConnectToServer();
}

void OnTick()
{
    if (socket == INVALID_HANDLE || !SocketIsConnected(socket))
    {
        Print("Socket not connected or invalid handle. Attempting to reconnect...");
        ConnectToServer();
        Sleep(10);
    }
    else
    {
        HTTPRecv(socket, 5000);
    }
}

void OnDeinit(const int reason)
{
    if (socket != INVALID_HANDLE)
    {
        SocketClose(socket);
        Print("Socket closed.");
    }
}
