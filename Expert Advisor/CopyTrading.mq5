#include <Trade\Trade.mqh>
#include <JAson.mqh>

CTrade trade;
CPositionInfo m_Position; 

string Address = "172.174.154.125";
//string Address = "127.0.0.1";
int Port = 9094;

double botVersion = 1.1;
bool ExtTLS = false;
int socket = INVALID_HANDLE;

input string Email_Address = "your.email@example.com"; 
input string Cell_Number = "1234567890"; 
input string Name_Surname = "John Doe"; 
input bool Auto_Lot_Size = 1.0; 
input double Lot_Size = 0.01; 
input string Identification_Number = "12345678910";

input bool Use_Trailing_SL = true; 

datetime lastPingTime = 0; 


#property description "Welcome to My Expert Advisor! Please configure the settings as needed."

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
        else if (jsCode == "ModifyTrade")
        {
            ModifyTrade(json);
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

   Print("Authenticate : " + json);

    CJAVal authenticateObj;
             authenticateObj["Code"] = "Authenticate";
             authenticateObj["AccountId"] = IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN));
             authenticateObj["Email"] = Email_Address;
             authenticateObj["CellNumber"] = Cell_Number;
             authenticateObj["Name"] = Name_Surname;
             authenticateObj["IdentificationNumber"] = Identification_Number;
             
             authenticateObj["AutoLotSize"] = Auto_Lot_Size;
             authenticateObj["LotSize"] = DoubleToString(Lot_Size);

             
    string ConnectedMessage = authenticateObj.Serialize();                      
    
    HTTPSend(socket, ConnectedMessage);
    
}

void OpenTrade(string json)
{
    Print("OpenTrade called with JSON: ", json);

    CJAVal jsonObj;

    if (jsonObj.Deserialize(json))
    {
        string symbol = jsonObj["Symbol"].ToStr();
        ENUM_ORDER_TYPE orderType = (ENUM_ORDER_TYPE)StringToInteger(jsonObj["Type"].ToStr());
        double volume = Lot_Size;
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
             CJAVal authenticateObj;
             authenticateObj["Code"] = "TradeStatus";
             authenticateObj["Ticket"] = IntegerToString(trade.ResultOrder());
             authenticateObj["Magic"] = magicNumber;
             authenticateObj["Symbol"] = symbol;
             authenticateObj["Type"] = IntegerToString(orderType);
             authenticateObj["Volume"] = DoubleToString(volume);
             authenticateObj["Comment"] = comment;
             
             string authenticateResponse = authenticateObj.Serialize();
         
             HTTPSend(socket, authenticateResponse); 
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

void ModifyTrade(string json)
{
    Print("ModifyTrade called with JSON: ", json);
    CJAVal jsonObj;

    if (jsonObj.Deserialize(json))
    {
         ModifyTradesByMagicNumber(jsonObj["magicNumber"].ToStr(),jsonObj["SL"].ToDbl());
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
                datetime positionTime = (datetime)PositionGetInteger(POSITION_TIME);
                string formattedTime = TimeToString(positionTime, TIME_DATE | TIME_MINUTES);

                trade.PositionClose(m_Position.Ticket());
                
                string TradeDetails = "{\"Code\": \"TradeProfit\", \"ClientID\": \"" + accountID + "\","
                                      "\"Ticket\": \"" + positionTicket + "\","
                                      "\"Symbol\": \"" + symbol + "\","
                                      "\"Volume\": \"" + volume + "\","
                                      "\"Profit\": \"" + profit + "\","
                                      "\"OrderTime\": \"" + formattedTime + "\","
                                      "\"MagicNumber\": \"" + positionMagicNumber + "\"}";
                
                HTTPSend(socket, TradeDetails);    
            }
        }
    }
}

void ModifyTradesByMagicNumber(string magicNumber,double SL)
{
    if (Use_Trailing_SL)
    {
       int totalPositions = PositionsTotal();
       
       for(int i = totalPositions - 1; i >= 0; i--)
       {
           if(m_Position.SelectByIndex(i))
           {
               ulong positionMagicNumber = PositionGetInteger(POSITION_MAGIC);
               
               if(positionMagicNumber == magicNumber)
               {
                   if(!trade.PositionModify(m_Position.Ticket(), SL, 0))
                   {
                       Print("Failed to modify position: ", m_Position.Ticket(), " Error: ", GetLastError());
                   }
               }
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
        Comment(message);
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

void Ping()
{
    datetime current_time = TimeCurrent();
    string time_str = TimeToString(current_time, TIME_DATE | TIME_MINUTES | TIME_SECONDS);
    Print("Ping server at ", time_str);
    
    string pingMessage = "{\"Code\":\"Ping\"}";
    HTTPSend(socket, pingMessage);
}

void ConnectToServer()
{
    socket = SocketCreate();
    long accountNumber = AccountInfoInteger(ACCOUNT_LOGIN);
       
    if (socket != INVALID_HANDLE && SocketConnect(socket, Address, Port, 1000))
    {
        Print("Connected to ", Address, ":", Port);
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
    if(GlobalVariableCheck("EA_Active"))
    {
        MessageBox("The EA is already running on another chart.", "EA", MB_OK);
        ExpertRemove();
    }
    else
    {
        GlobalVariableSet("EA_Active", 1);
    }

    ConnectToServer();
    lastPingTime = TimeCurrent(); // Initialize the last ping time
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

    if (TimeCurrent() - lastPingTime >= 60)
    {
        Ping();
        lastPingTime = TimeCurrent();
    }
}

void OnDeinit(const int reason)
{
    if(GlobalVariableCheck("EA_Active"))
    {
        GlobalVariableDel("EA_Active");
    }
    
    if (socket != INVALID_HANDLE)
    {
        SocketClose(socket);
        Print("Socket closed.");
    }
}
