#include <Trade\Trade.mqh>
#include <JAson.mqh>

CTrade trade;
CPositionInfo m_Position; 

string Address = "127.0.0.1";
int Port = 9094;

double botVersion = 1.1;
bool ExtTLS = false;
int socket = INVALID_HANDLE;

input string Email_Address = "your.email@example.com"; 
input string Cell_Number = "1234567890"; 
input string Name_Surname = "John Doe"; 
input bool Auto_Lot_Size = 1.0; 
input double Lot_Size = 1.0; 

void RequestHandler(string json)
{

    CJAVal jsonObj;

    if (jsonObj.Deserialize(json))
    {
        string jsCode = jsonObj["Code"].ToStr();

        if (jsCode == "OpenTrade")
        {
            OpenTrade(json);
        }
        else if (jsCode == "CloseTrade")
        {
            CloseTrade(json);
        }
        else if (jsCode == "Notifications")
        {
            Notification(json);
        }
        else if (jsCode == "Authenticate")
        {
            Authenticate(json);
        }
        else
        {
            Print(json);
        }
    }
    else
    {
        Print("Failed to deserialize JSON");
    }
}

void Authenticate(string json)
{
    Print("Authenticate")
}

void OpenTrade(string json)
{
    Print("OpenTrade called with JSON: ", json);

    CJAVal jsonObj;

    if (jsonObj.Deserialize(json))
    {
        string symbol = jsonObj["Symbol"].ToStr();
        ENUM_ORDER_TYPE orderType = (ENUM_ORDER_TYPE)StringToInteger(jsonObj["Type"].ToStr());
        double volume = jsonObj["Volume"].ToDbl();
        double price = jsonObj["Open Price"].ToDbl();
        double sl = jsonObj["SL"].ToDbl(); 
        double tp = jsonObj["TP"].ToDbl(); 
        string comment = jsonObj["Comment"].ToStr();
        string magicNumber = jsonObj["Ticket"].ToStr();
      
        bool result = false;
        switch(orderType)
        {
            case ORDER_TYPE_BUY:
                trade.SetExpertMagicNumber(magicNumber);   
                result = trade.Buy(volume, symbol, price, sl, tp, comment);
                break;
            case ORDER_TYPE_SELL:
                trade.SetExpertMagicNumber(magicNumber);   
                result = trade.Sell(volume, symbol, price, sl, tp, comment);
                break;
            default:
                Print("Unsupported order type: ", orderType);
                return;
        }

        if(!result)
         {
             Print("Trade execution failed: ", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription());
         }
         else
         {
             // Create a JSON object for success response
             string successResponse = "{ \"Code\": \"TradeStatus\", \"Status\": \"True\" }";
         
             // Send the success JSON back through HTTP
             HTTPSend(socket, successResponse); 
         }

        
    }
    else
    {
        Print("Failed to deserialize JSON: ", json);
    }
}

void CloseTrade(string json)
{
    Print("CloseTrade called with JSON: ", json);
    CJAVal jsonObj;

    if (jsonObj.Deserialize(json))
    {
         CloseTradesByMagicNumber(jsonObj["Ticket"].ToStr());
    }
}

void CloseTradesByMagicNumber(string magicNumber)
{
    int totalPositions = PositionsTotal();
    
    for(int i = totalPositions - 1; i >= 0; i--)
    {
        if(m_Position.SelectByIndex(i))
        {
            ulong positionMagicNumber = PositionGetInteger(POSITION_MAGIC);

            if(positionMagicNumber == magicNumber)
            {
                ulong positionTicket = PositionGetInteger(POSITION_TICKET);
                string symbol = PositionGetString(POSITION_SYMBOL);
                double volume = PositionGetDouble(POSITION_VOLUME);
                double profit = PositionGetDouble(POSITION_PROFIT);
                ulong accountID = AccountInfoInteger(ACCOUNT_LOGIN);

                trade.PositionClose(m_Position.Ticket());
                
                string TradeDetails = "{\"Code\": \"TradeProfit\", \"ClientID\": \"" + accountID + "\","
                                      "\"Ticket\": \"" + positionTicket + "\","
                                      "\"Symbol\": \"" + symbol + "\","
                                      "\"Volume\": \"" + volume + "\","
                                      "\"Profit\": \"" + profit + "\","
                                      "\"MagicNumber\": \"" + positionMagicNumber + "\"}";
                
                HTTPSend(socket, TradeDetails);    
            }
        }
    }
}


void Notification(string json)
{
    Print("Notification called with JSON: ", json);

    CJAVal jsonObj;

    if (jsonObj.Deserialize(json)) 
    {
        // Extract some information from the JSON object for display
        string message = jsonObj["message"].ToStr();
        Comment("Message: ", message);
    } 
    else 
    {
        Print("Failed to deserialize JSON in Notification: ", json);
    }
}




bool HTTPSend(int socket, string request)
{
    char req[];

    int len = StringToCharArray(request, req) - 1;

    return (len >= 0) && ((ExtTLS ? SocketTlsSend(socket, req, len) : SocketSend(socket, req, len)) == len);
}

bool HTTPRecv(int socket, uint timeout)
{
    char rsp[2000];  // Buffer size set to 2000 to handle large messages
    string buffer = "";  // Buffer to accumulate incoming data
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

                // Check for complete JSON messages in the buffer
                while (true)
                {
                    int start_pos = StringFind(buffer, "{");
                    int end_pos = StringFind(buffer, "}");

                    if (start_pos != -1 && end_pos != -1 && end_pos > start_pos)
                    {
                        // Extract complete JSON message
                        string complete_json = StringSubstr(buffer, start_pos, end_pos - start_pos + 1);
                        RequestHandler(complete_json);

                        // Remove processed JSON message from buffer
                        buffer = StringSubstr(buffer, end_pos + 1);
                    }
                    else
                    {
                        break;  // No complete JSON message found, exit the loop
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

    return StringLen(buffer) > 0;
}


void ConnectToServer()
{
    socket = SocketCreate();
    long accountNumber = AccountInfoInteger(ACCOUNT_LOGIN);
       
    if (socket != INVALID_HANDLE && SocketConnect(socket, Address, Port, 1000))
    {
        Print("Connected to ", Address, ":", Port);

        long account_id = AccountInfoInteger(ACCOUNT_LOGIN);

        string ConnectedMessage = "{\"Code\": \"ClientConnected\", \"ClientID\": \"" + IntegerToString(account_id) + "\", " +
                          "\"Email\": \"" + Email_Address + "\", " +
                          "\"CellNumber\": \"" + Cell_Number + "\", " +
                          "\"NameSurname\": \"" + Name_Surname + "\", " +
                          "\"AutoLotSize\": " + (Auto_Lot_Size ? "true" : "false") + ", " +
                          "\"LotSize\": " + DoubleToString(Lot_Size) + "}";

         HTTPSend(socket, ConnectedMessage);


        string subject, issuer, serial, thumbprint;
        datetime expiration;

        if (SocketTlsCertificate(socket, subject, issuer, serial, thumbprint, expiration))
        {
            Print("TLS certificate:\nOwner: ", subject, "\nIssuer: ", issuer, "\nNumber: ", serial, "\nPrint: ", thumbprint, "\nExpiration: ", expiration);
            ExtTLS = true;
        }
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
        if (HTTPRecv(socket, 5000))
        {
 
        }
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
