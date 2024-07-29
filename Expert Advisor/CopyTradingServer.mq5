#include <TradeInfo.mqh>
#include <Trade\Trade.mqh>
#include <JAson.mqh>
#include <stdlib.mqh>

CTrade trade;

//string Address = "127.0.0.1";
string Address = "172.174.154.125";

int Port = 9094;
bool ExtTLS = false;
int socket = INVALID_HANDLE;

string Email_Address = "Server.email@example.com"; 
string Cell_Number = "1234567890"; 
string Name_Surname = "Server"; 
string Identification_Number = "Server";

datetime lastPingTime = 0;

TradeInfo trades[];

bool authenticated = false;

int OnInit()
{
    ConnectToServer();

    int total = PositionsTotal();
    
    for (int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i); 
        
        if (PositionSelectByTicket(ticket))
        {
            CreateTrade(ticket,  PositionGetInteger(POSITION_TICKET),PositionGetInteger(POSITION_TYPE),PositionGetDouble(POSITION_PRICE_OPEN), PositionGetDouble(POSITION_VOLUME), PositionGetString(POSITION_SYMBOL), PositionGetInteger(POSITION_TIME),trades);
        }
    }
    
    //Scheduled tasks
    EventSetTimer(60);
    
    return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
    EventKillTimer();
}

void OnTick()
{
   if (socket == INVALID_HANDLE || !SocketIsConnected(socket))
    {
        Print("Socket not connected or invalid handle. Attempting to reconnect...");
        ConnectToServer();
        Sleep(10);
    }
    else if(!authenticated)
    {   
        if (HTTPRecv(socket, 5000))
        {
            
        }
    }

   int size = ArraySize(trades);
   
   for(int i = 0; i < size; i++)
   {
      if(PositionSelectByTicket(trades[i].positionID) )
      {         
         if( trades[i].symbol == "")
         {
            UpdateTradeDetailsByPosition(trades[i].positionID,
                                            PositionGetInteger(POSITION_TICKET),
                                            PositionGetInteger(POSITION_TYPE),
                                            PositionGetDouble(POSITION_PRICE_OPEN),
                                            PositionGetDouble(POSITION_VOLUME),
                                            PositionGetString(POSITION_SYMBOL),
                                            PositionGetInteger(POSITION_TIME),
                                            PositionGetDouble(POSITION_SL),
                                            trades);  
         }
         else
         {
            double currentProfit = PositionGetDouble(POSITION_PROFIT);
            double maxProfit = GetMaxProfitByPositionID(trades[i].positionID, trades);
            double minDrawdown = GetDrawdownProfitByPositionID(trades[i].positionID, trades);
            
            if(currentProfit > maxProfit && currentProfit > 0)
            {
                Print("New Max profit");
                PrintFormat("Current Profit: %.2f, Max Profit: %.2f", currentProfit, maxProfit);
                UpdateTradeProfitOrDrawdown(trades[i].positionID, currentProfit, true, trades);
            }
            
            if(currentProfit < minDrawdown && currentProfit < 0)
            {
                Print("New Min profit");
                PrintFormat("Current Profit: %.2f, Min Drawdown: %.2f", currentProfit, minDrawdown);
                UpdateTradeProfitOrDrawdown(trades[i].positionID, currentProfit, false, trades);
            }
            
            UpdateTradeProfit(trades[i].positionID,currentProfit, trades);

                        
         }
                
      }
      
   }
}

void OnTimer()
{
   int targetHour1 = 9; 
   int targetMinute1 = 0; 

   int intervalUpdateTrades = 1;  
   int intervalPing = 10; 

   datetime currentTime = TimeCurrent();
   MqlDateTime currentTimeStruct;
   TimeToStruct(currentTime, currentTimeStruct);

   int currentHour = currentTimeStruct.hour;
   int currentMinute = currentTimeStruct.min;

   if(currentHour == targetHour1 && currentMinute == targetMinute1)
   {
      Print("Executing first script at: ", TimeToString(currentTime, TIME_MINUTES));
   }

   if(currentMinute % intervalUpdateTrades == 0)
   {
      UpdateTradesFromHistory();
   }
   
   if(currentMinute % intervalPing == 0)
   {
      Print("Ping");
      //authenticated = false;
      
      string pingMessage = "{\"Code\":\"PingFromServer\"}";
      HTTPSend(socket, pingMessage);
      
   }
}



void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
{

   switch(trans.type)
   {
      case TRADE_TRANSACTION_DEAL_UPDATE:
      
         if (PositionSelectByTicket(trans.position)) 
            {
            
                CJAVal authenticateObj;
                authenticateObj["Code"] = "Server_UpdateTrade";
                authenticateObj["AccountId"] = IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN));
                authenticateObj["Ticket"] = IntegerToString(PositionGetInteger(POSITION_IDENTIFIER));
                authenticateObj["TP"] = DoubleToString(PositionGetDouble(POSITION_TP));
                authenticateObj["SL"] = DoubleToString(PositionGetDouble(POSITION_SL));
                 
                string OpenTrade = authenticateObj.Serialize();                      
                HTTPSend(socket, OpenTrade);
                
            } 
            else {
                Print("Position with ticket ", trans.position, " not found.");
            }
         
      case TRADE_TRANSACTION_DEAL_ADD:
      
         if(PositionIDExists(trans.position, trades))
         {
            
           Print("Closed Trade: Position ID = ", trans.position);  
                  
           CJAVal authenticateObj;
           authenticateObj["Code"] = "Server_CloseTrade";
           authenticateObj["AccountId"] = IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN));
           authenticateObj["Ticket"] = GetTicketByPositionID(trans.position, trades);
           authenticateObj["Symbol"] = GetSymbolByPositionID(trans.position, trades);
           authenticateObj["Type"] = GetTypeByPositionID(trans.position, trades); 
           //authenticateObj["profit"] = GetProfitByPositionID(trans.position, trades);
           authenticateObj["maxDrawdown"] = GetDrawdownProfitByPositionID(trans.position, trades);
           authenticateObj["maxProfit"] = GetMaxProfitByPositionID(trans.position, trades);
           
           MqlDateTime dt;
           TimeToStruct(TimeCurrent(), dt);
           authenticateObj["Close Time"] = StringFormat("%04d-%02d-%02d %02d:%02d:%02d", dt.year, dt.mon, dt.day, dt.hour, dt.min, dt.sec); 
                                    
           string CloseTrade = authenticateObj.Serialize();                      
           HTTPSend(socket, CloseTrade);
       
           RemoveTradeByPositionID(trans.position, trades);

         }
         else
         {
            CreateTradeWithPositionID(trans.position,trades);
            Print("Opened Trade: Position ID = ", trans.position);
     
            
            if (PositionSelectByTicket(trans.position)) 
            {
            
                CJAVal authenticateObj;
                authenticateObj["Code"] = "Server_OpenTrade";
                authenticateObj["AccountId"] = IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN));
                authenticateObj["Ticket"] = IntegerToString(PositionGetInteger(POSITION_IDENTIFIER));
                authenticateObj["Symbol"] = PositionGetString(POSITION_SYMBOL);
                authenticateObj["Type"] = PositionGetInteger(POSITION_TYPE);
                authenticateObj["Open Price"] = PositionGetDouble(POSITION_PRICE_OPEN);     
                authenticateObj["Comment"] = PositionGetString(POSITION_COMMENT);
                authenticateObj["Magic"] = IntegerToString(PositionGetInteger(POSITION_MAGIC));
                authenticateObj["TP"] = DoubleToString(PositionGetDouble(POSITION_TP));
                authenticateObj["SL"] = DoubleToString(PositionGetDouble(POSITION_SL));
                
                MqlDateTime dt;
                TimeToStruct(TimeCurrent(), dt);
                authenticateObj["Open Time"] = StringFormat("%04d-%02d-%02d %02d:%02d:%02d", dt.year, dt.mon, dt.day, dt.hour, dt.min, dt.sec); 
                 
                string OpenTrade = authenticateObj.Serialize();                      
                HTTPSend(socket, OpenTrade);
                
            } 
            else {
                Print("Position with ticket ", trans.position, " not found.");
            }


         }
         break;

   }

}

//===================================================================================================================================

void RequestHandler(string json)
{
    CJAVal jsonObj;

    if (jsonObj.Deserialize(json))
    {
        string jsCode = jsonObj["Code"].ToStr();

        if (jsCode == "Authenticate")
        {
            Authenticate(json);
        }
        if (jsCode == "Notifications")
        {
            Print("Ping result");
            Sleep(10);
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

    string ConnectedMessage = authenticateObj.Serialize();                      
    
    authenticated = true;
    
    HTTPSend(socket, ConnectedMessage);

}

bool HTTPSend(int socket, string request)
{
    char req[];

    int len = StringToCharArray(request, req) - 1;

    // Ensure the length is non-negative
    if (len < 0)
        return false;

    // Convert the length to a 4-byte array in big-endian format
    uchar len_bytes[4];
    len_bytes[0] = (uchar)((len >> 24) & 0xFF);
    len_bytes[1] = (uchar)((len >> 16) & 0xFF);
    len_bytes[2] = (uchar)((len >> 8) & 0xFF);
    len_bytes[3] = (uchar)(len & 0xFF);

    // Create a new array to hold the length prefix and the message
    char prefixed_req[];
    ArrayResize(prefixed_req, 4 + len);

    // Copy the length bytes into the prefixed request array
    for (int i = 0; i < 4; i++)
        prefixed_req[i] = len_bytes[i];

    // Copy the original request bytes into the prefixed request array
    for (int i = 0; i < len; i++)
        prefixed_req[4 + i] = req[i];

    // Calculate the total length of the final message
    int total_len = 4 + len;

    // Print the byte size of the final message
    Print("Byte size of the final message: " + IntegerToString(total_len));

    // Send the prefixed request
    return (ExtTLS ? SocketTlsSend(socket, prefixed_req, total_len) : SocketSend(socket, prefixed_req, total_len)) == total_len;
}

bool HTTPRecv(int socket, uint timeout)
{
    char rsp[300];  // Buffer size set to 2000 to handle large messages
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
                        Print(complete_json);

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
    }
    else
    {
        Print("Connection to ", Address, ":", Port, " failed, error ", GetLastError());
        SocketClose(socket);
        socket = INVALID_HANDLE;
    }
}

//===================================================================================================================================



void UpdateTradesFromHistory()
{
int tradesIncluded = 15;

datetime DateFrom = TimeCurrent() - 86400; 
datetime DateTo = TimeCurrent() + 2 * 86400;

if (HistorySelect(DateFrom, DateTo))
{
    int totalDeals = HistoryDealsTotal();
    int maxTradesPerBatch = tradesIncluded;
    int totalBatches = (totalDeals + maxTradesPerBatch - 1) / maxTradesPerBatch;

    for (int batch = 0; batch < totalBatches; batch++)
    {
        string jsonTradesArray = "[";
        int start = batch * maxTradesPerBatch;
        int end = MathMin(start + maxTradesPerBatch, totalDeals);

        for (int i = start; i < end; i++)
        {
            ulong ticket = HistoryDealGetTicket(i);
            ulong positionID =  HistoryDealGetInteger(ticket, DEAL_POSITION_ID);
            ulong type = HistoryDealGetInteger(ticket, DEAL_TYPE);
            string symbol = HistoryDealGetString(ticket, DEAL_SYMBOL);
            double volume = HistoryDealGetDouble(ticket, DEAL_VOLUME);
            double profit = HistoryDealGetDouble(ticket, DEAL_PROFIT);
            ulong accountID = AccountInfoInteger(ACCOUNT_LOGIN);
            datetime positionTime = (datetime)HistoryDealGetInteger(ticket, DEAL_TIME);
            ulong positionMagicNumber = HistoryDealGetInteger(ticket, DEAL_MAGIC);
            double swap = HistoryDealGetDouble(ticket, DEAL_SWAP);
            double TP = HistoryDealGetDouble(ticket, DEAL_TP);
            double SL = HistoryDealGetDouble(ticket, DEAL_SL);

            if (i > start)
                jsonTradesArray += ",";

            jsonTradesArray += StringFormat(
                "{\"Ticket\":\"%I64u\",\"Type\":\"%I64u\",\"Symbol\":\"%s\",\"Profit\":\"%.2f\",\"Volume\":\"%.2f\",\"AccountID\":\"%I64u\",\"Magic\":\"%I64u\",\"Swap\":\"%.2f\",\"TP\":\"%.2f\",\"SL\":\"%.2f\",\"PositionTime\":\"%s\"}",
                positionID, type, symbol, profit, volume, accountID, positionMagicNumber, swap,TP,SL, TimeToString(positionTime, TIME_DATE | TIME_MINUTES)
            );
            
            
        }

        jsonTradesArray += "]";

        string finalJsonStr = StringFormat("{\"Code\":\"Server_TradeHistory\",\"Trades\":%s}", jsonTradesArray);

        HTTPSend(socket, finalJsonStr);
        Print("Sent JSON to server: " + finalJsonStr);

        Sleep(100); 
    }
}
else
{
    Print("Failed to select history for the given date range");
}

}
