#include <Trade\Trade.mqh>
#include <JAson.mqh>
#include <stdlib.mqh>

CTrade trade;
CPositionInfo m_Position; 

string Address = "172.174.154.125";
//string Address = "127.0.0.1";
int Port = 9094;

double botVersion = 1.2;
bool ExtTLS = false;
int socket = INVALID_HANDLE;

input string Email_Address = "your.email@example.com"; 
input string Cell_Number = "1234567890"; 
input string Name_Surname = "John Doe"; 
input bool Auto_Lot_Size = 1.0; 
input double Lot_Size = 0.01; 
input string Identification_Number = "12345678910";

input int MaxTrades = 100;
input int MaxBuyTrades = 0;
input int MaxSellTrades = 0;

input double SL_DifferenceMultiplier = 1000; //points 1 point = 1$ on 0.01
input double TP_DifferenceMultiplier = 1000;

input bool Use_Trailing_SL = true; 
input bool Change_Order_When_Master_Change_SL_OR_TP = true; 

datetime lastPingTime = 0; 


#property description "Welcome to My Expert Advisor! Please configure the settings as needed."

void RequestHandler(string json)
{
    CJAVal jsonObj;
    
    Print(json);

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
        else if (jsCode == "ModifyTradeSLTP")
        {
            ModifyTradeSLTP(json);
        }
        else if (jsCode == "AccountHistory")
        {
            Print("History Requested");
            AccountHistory(json);
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

int CountOpenTradesByType(ENUM_ORDER_TYPE orderType)
{
    int count = 0;
    for (int i = 0; i < PositionsTotal(); i++)
    {
        if (m_Position.SelectByIndex(i))
        {
            // Convert the order type to the corresponding position type
            if ((orderType == ORDER_TYPE_BUY && m_Position.PositionType() == POSITION_TYPE_BUY) ||
                (orderType == ORDER_TYPE_SELL && m_Position.PositionType() == POSITION_TYPE_SELL))
            {
                count++;
            }
        }
    }
    return count;
}




// Define the configurable SL and TP difference multipliers


bool Validation(string symbol, ENUM_ORDER_TYPE orderType, double price, double sl, double tp)
{
    
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);

    int openTrades = PositionsTotal();
    
    //MAX TRADE VALIDATION
    if(openTrades >= MaxTrades) 
    {
        Print("Too many open trades.");
        return false;
    }
    
    
    int openBuyTrades = CountOpenTradesByType(ORDER_TYPE_BUY);
    int openSellTrades = CountOpenTradesByType(ORDER_TYPE_SELL);
   
    if (orderType == ORDER_TYPE_BUY && openBuyTrades >= MaxBuyTrades)
    {
       Print("Too many open buy trades.");
       return false;
    }
   
    if (orderType == ORDER_TYPE_SELL && openSellTrades >= MaxSellTrades)
    {
       Print("Too many open sell trades.");
       return false;
    }
    
    

    //TP AND SL Validations
    if(orderType == ORDER_TYPE_BUY)
    {
        if (sl != 0 && (sl >= price || MathAbs(price - sl) < SL_DifferenceMultiplier * point))
        {
            Print("Invalid Stop Loss for BUY order.");
            return false;
        }
        if (tp != 0 && (tp <= price || MathAbs(tp - price) < TP_DifferenceMultiplier * point))
        {
            Print("Invalid Take Profit for BUY order.");
            return false;
        }
    }
    else if(orderType == ORDER_TYPE_SELL)
    {
        if (sl != 0 && (sl <= price || MathAbs(sl - price) < SL_DifferenceMultiplier * point))
        {
            Print("Invalid Stop Loss for SELL order.");
            return false;
        }
        if (tp != 0 && (tp >= price || MathAbs(price - tp) < TP_DifferenceMultiplier * point))
        {
            Print("Invalid Take Profit for SELL order.");
            return false;
        }
    }
    
    return true;
}


void OpenTrade(string json)
{
    Print("OpenTrade called with JSON: ", json);

    CJAVal jsonObj;

    if (jsonObj.Deserialize(json))
    {
        string symbol = jsonObj["Symbol"].ToStr();
        ENUM_ORDER_TYPE orderType = (ENUM_ORDER_TYPE)StringToInteger(jsonObj["Type"].ToStr());
        double price = jsonObj["Open Price"].ToDbl();
        double sl = jsonObj["SL"].ToDbl();
        double tp = jsonObj["TP"].ToDbl();
        string comment = jsonObj["Comment"].ToStr();
        ulong magicNumber = StringToInteger(jsonObj["Ticket"].ToStr());

        if (!Validation(symbol, orderType, price, sl, tp))
        {
            Print("Trade validation failed.");
            return; 
        }

        double volume = Lot_Size;
        bool result = false;
        trade.SetExpertMagicNumber(magicNumber);

        switch(orderType)
        {
            case ORDER_TYPE_BUY:
                result = trade.Buy(volume, symbol, price, sl, tp, comment);
                break;
            case ORDER_TYPE_SELL:
                result = trade.Sell(volume, symbol, price, sl, tp, comment);
                break;
        }

        if (!result)
        {
            Print("Trade execution failed: ", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription());
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
         ModifyTradesByMagicNumber(jsonObj["magicNumber"].ToStr(),jsonObj["SL"].ToDbl(),jsonObj["TP"].ToDbl());
    }
}
void ModifyTradeSLTP(string json)
{
    Print("ModifyTrade SL TP called with JSON: ", json);
    CJAVal jsonObj;

    if (jsonObj.Deserialize(json))
    {
         ModifyTradesSLTPByMagicNumber(jsonObj["magicNumber"].ToStr(),jsonObj["SL"].ToDbl(),jsonObj["TP"].ToDbl());
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
            }
        }
    }
}

void ModifyTradesByMagicNumber(string magicNumber,double SL,double TP)
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
                   if(!trade.PositionModify(m_Position.Ticket(), SL, TP))
                   {
                       Print("Failed to modify position: ", m_Position.Ticket(), " Error: ", GetLastError());
                   }
               }
           }
       }
    }    
}

void ModifyTradesSLTPByMagicNumber(string magicNumber,double SL,double TP)
{
    if (Change_Order_When_Master_Change_SL_OR_TP)
    {
       int totalPositions = PositionsTotal();
       
       for(int i = totalPositions - 1; i >= 0; i--)
       {
           if(m_Position.SelectByIndex(i))
           {
               ulong positionMagicNumber = PositionGetInteger(POSITION_MAGIC);
               
               if(positionMagicNumber == magicNumber)
               {
                   if(!trade.PositionModify(m_Position.Ticket(), SL, TP))
                   {
                       Print("Failed to modify position SLTP: ", m_Position.Ticket(), " Error: ", GetLastError());
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
        string message = jsonObj["message"].ToStr();
        Comment(message);
        
        if(jsonObj["popup"].ToStr() != "")
        {
            MessageBox(jsonObj["popup"].ToStr(), "Popup", MB_OK);
        }
        
        if(jsonObj["removeEA"].ToStr() == "1")
        {
            ExpertRemove();
        }
    } 
    else 
    {
        Print("Failed to deserialize JSON in Notification: ", json);
    }
}

void AccountHistory(string json)
{
    Print("Account History Requested");
    Print(json);

    CJAVal jsonObj;

    if (jsonObj.Deserialize(json))
    {
        string dateFromStr = jsonObj["From"].ToStr();
        string dateToStr = jsonObj["To"].ToStr();        
        int tradesIncluded = jsonObj["TradesIncluded"].ToInt();
         
        datetime DateFrom = StringToTime(dateFromStr);
        datetime DateTo = StringToTime(dateToStr);

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
                    ulong type = HistoryDealGetInteger(ticket, DEAL_TYPE);
                    string symbol = HistoryDealGetString(ticket, DEAL_SYMBOL);
                    double volume = HistoryDealGetDouble(ticket, DEAL_VOLUME);
                    double profit = HistoryDealGetDouble(ticket, DEAL_PROFIT);
                    ulong accountID = AccountInfoInteger(ACCOUNT_LOGIN);
                    datetime positionTime = (datetime)HistoryDealGetInteger(ticket, DEAL_TIME);
                    ulong positionMagicNumber = HistoryDealGetInteger(ticket, DEAL_MAGIC);
                    double swap = HistoryDealGetDouble(ticket, DEAL_SWAP);

                    if (i > start)
                        jsonTradesArray += ",";

                    jsonTradesArray += "{\"Ticket\":\"" + IntegerToString(ticket) + "\",";
                    jsonTradesArray += "\"Type\":\"" + IntegerToString(type) + "\",";
                    jsonTradesArray += "\"Symbol\":\"" + symbol + "\",";
                    jsonTradesArray += "\"Profit\":\"" + DoubleToString(profit) + "\",";
                    jsonTradesArray += "\"Volume\":\"" + DoubleToString(volume) + "\",";
                    jsonTradesArray += "\"AccountID\":\"" + IntegerToString(accountID) + "\",";
                    jsonTradesArray += "\"Magic\":\"" + IntegerToString(positionMagicNumber) + "\",";
                    jsonTradesArray += "\"Swap\":\"" + DoubleToString(swap) + "\",";
                    jsonTradesArray += "\"PositionTime\":\"" + TimeToString(positionTime, TIME_DATE | TIME_MINUTES) + "\"}";
                }

                jsonTradesArray += "]";

                string finalJsonStr = "{\"Code\":\"AccountHistory\",\"Trades\":" + jsonTradesArray + "}";

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
    else
    {
        Print("Failed to deserialize JSON");
    }
}






bool HTTPSend(int socket, string request)
{
    char req[];

    // Convert the request string to a char array
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


bool HTTPRecv(int socket, uint timeout) {
    uchar response[];  // Accumulate the data as a whole (headers + body)
    uchar block[];     // Separate read block
    int len;           // Current block size
    int lastLF = -1;   // Position of the last line feed found
    int body = 0;      // Offset where document body starts
    int size = -1;     // Document size according to Content-Length
    string result = ""; // Result of the HTTP message
    const static string content_length = "Content-Length:";
    const static string crlf = "\r\n";
    const static int crlf_length = 2;

    uint start = GetTickCount();
    do {
        ResetLastError();
        len = (ExtTLS ? SocketTlsReadAvailable(socket, block, 1024) : SocketReadAvailable(socket, block, 1024));
        if (len > 0) {
            const int n = ArraySize(response);
            ArrayResize(response, n + len); // Resize the response array
            ArrayCopy(response, block, n);  // Append the new block to response

            // Parse multiple messages
            while (true) {
                // Parse headers to find the body start
                if (body == 0) { // Look for the completion of the headers
                    for (int i = n; i < ArraySize(response); ++i) {
                        if (response[i] == '\n') { // LF
                            if (lastLF == i - crlf_length) { // Found sequence "\r\n\r\n"
                                body = i + 1;
                                string headers = CharArrayToString(response, 0, i);
                                Print("* HTTP-header found, header size: ", body);
                                Print(headers);
                                const int p = StringFind(headers, content_length);
                                if (p > -1) {
                                    int end_of_line = StringFind(headers, crlf, p);
                                    if (end_of_line == -1)
                                        end_of_line = StringLen(headers);
                                    size = (int)StringToInteger(StringSubstr(headers, p + StringLen(content_length), end_of_line - p - StringLen(content_length)));
                                    Print("* ", content_length, size);
                                } else {
                                    size = -1; // Server did not provide document length
                                }
                                break; // Header/body boundary found
                            }
                            lastLF = i;
                        }
                    }
                }

                // Check if the full body is received
                if (size > -1 && ArraySize(response) - body >= size) {
                    Print("* Complete document received");
                    result = CharArrayToString(response, body, size, CP_UTF8);
                    if (StringLen(result) > 0) {
                        RequestHandler(result);
                        Print(result);
                    }

                    // Remove processed message from response array
                    int processed_size = body + size;
                    if (ArraySize(response) > processed_size) {
                        ArrayCopy(response, response, 0, processed_size, ArraySize(response) - processed_size);
                        ArrayResize(response, ArraySize(response) - processed_size);
                    } else {
                        ArrayResize(response, 0);
                    }
                    
                    // Reset for next message
                    body = 0;
                    size = -1;
                    lastLF = -1;
                } else {
                    break; // Exit while loop if no complete message is left
                }
            }
        } else {
            if (len == 0) Sleep(10); // Wait a bit for more data
        }
    } while (GetTickCount() - start < timeout && !IsStopped() && !_LastError);

    return StringLen(result) > 0;
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

//-------------------------------EXTRA FUNCTINOS REQUIRED-------------------------------

int SocketReadAvailable(int socket, uchar &block[], const uint maxlen = INT_MAX)
{
   ArrayResize(block, 0);
   const uint len = SocketIsReadable(socket);
   if(len > 0)
      return SocketRead(socket, block, fmin(len, maxlen), 10);
   return 0;
}

int HexStringToInteger(const string hexString) 
{
    int result = 0;
    int length = StringLen(hexString);

    for (int i = 0; i < length; i++) {
        char c = hexString[i];
        int value;

        if (c >= '0' && c <= '9') {
            value = c - '0';
        } else if (c >= 'a' && c <= 'f') {
            value = c - 'a' + 10;
        } else if (c >= 'A' && c <= 'F') {
            value = c - 'A' + 10;
        } else {
            Print("Invalid hexadecimal character: ", c);
            return 0; // Handle invalid characters
        }

        result = result * 16 + value;
    }

    return result;
}