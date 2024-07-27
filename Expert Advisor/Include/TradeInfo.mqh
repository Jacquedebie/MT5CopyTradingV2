#ifndef __TRADEINFO_MQH__
#define __TRADEINFO_MQH__

struct TradeInfo
{
   ulong positionID;
   ulong ticketNr;   
   ulong type;   
   double openPrice;
   double volume;
   double maxProfit;
   double maxDrawdown;
   double profit;       
   string symbol;
   datetime openTime;
};

//-------------INSERT-------------

void CreateTrade(ulong positionID, ulong ticketNr,ulong type ,double openPrice, double volume, string symbol, datetime openTime, TradeInfo &trades[])
{
    TradeInfo trade;
    trade.positionID = positionID;
    trade.ticketNr = ticketNr; // Initialize ticket number
    trade.type = type;
    trade.openPrice = openPrice;
    trade.volume = volume;
    trade.maxProfit = 0;
    trade.maxDrawdown = 0;
    trade.profit = 0;         // Initialize profit
    trade.symbol = symbol;
    trade.openTime = openTime;

    int size = ArraySize(trades);
    ArrayResize(trades, size + 1);
    trades[size] = trade;
}

void CreateTradeWithPositionID(ulong positionID, TradeInfo &trades[])
{
   int size = ArraySize(trades);
   ArrayResize(trades, size + 1);
   
   trades[size].positionID = positionID;
   trades[size].ticketNr = 0; // Initialize ticket number
   trades[size].type = 0;
   trades[size].openPrice = 0.0;
   trades[size].volume = 0.0;
   trades[size].maxProfit = 0.0;
   trades[size].maxDrawdown = 0.0;
   trades[size].profit = 0.0; // Initialize profit
   trades[size].symbol = "";
   trades[size].openTime = 0;
}

//-------------DELETE-------------
bool RemoveTradeByPositionID(ulong positionID, TradeInfo &trades[])
{
   int size = ArraySize(trades);
   for(int i = 0; i < size; i++)
   {
      if(trades[i].positionID == positionID)
      {
         for(int j = i; j < size - 1; j++)
         {
            trades[j] = trades[j + 1];
         }
         ArrayResize(trades, size - 1);
         return true;
      }
   }
   return false;
}

//-------------SELECT-------------

bool PositionIDExists(ulong positionID, const TradeInfo &trades[])
{
   for(int i = 0; i < ArraySize(trades); i++)
   {
      if(trades[i].positionID == positionID)
      {
         return true;
      }
   }
   return false;
}

double GetMaxProfitByPositionID(ulong positionID, const TradeInfo &trades[])
{
    int size = ArraySize(trades);
    
    for(int i = 0; i < size; i++)
    {
        if(trades[i].positionID == positionID)
        {
            return trades[i].maxProfit;
        }
    }

    return -1;
}

double GetDrawdownProfitByPositionID(ulong positionID, const TradeInfo &trades[])
{
    int size = ArraySize(trades);
    
    for(int i = 0; i < size; i++)
    {
        if(trades[i].positionID == positionID)
        {
            return trades[i].maxDrawdown;  
        }
    }

    return -1;
}

double GetProfitByPositionID(ulong positionID, const TradeInfo &trades[])
{
    int size = ArraySize(trades);
    
    for(int i = 0; i < size; i++)
    {
        if(trades[i].positionID == positionID)
        {
            return trades[i].profit;
        }
    }

    return -1;
}


string GetSymbolByPositionID(ulong positionID, const TradeInfo &trades[])
{
    int size = ArraySize(trades);
    
    for(int i = 0; i < size; i++)
    {
        if(trades[i].positionID == positionID)
        {
            return trades[i].symbol;
        }
    }

    PrintFormat("Trade with PositionID %d not found.", positionID);
    return "";
}

string GetTypeByPositionID(ulong positionID, const TradeInfo &trades[])
{
    int size = ArraySize(trades);
    
    for(int i = 0; i < size; i++)
    {
        if(trades[i].positionID == positionID)
        {
            return trades[i].type;
        }
    }

    PrintFormat("Trade with PositionID %d not found.", positionID);
    return "";
}

string GetTicketByPositionID(ulong positionID, const TradeInfo &trades[])
{
    int size = ArraySize(trades);
    
    for(int i = 0; i < size; i++)
    {
        if(trades[i].positionID == positionID)
        {
            return trades[i].ticketNr;
        }
    }

    PrintFormat("Trade with PositionID %d not found.", positionID);
    return "";
}


//-------------UPDATE-------------

void UpdateTradeProfitOrDrawdown(ulong positionID, double value, bool updateMaxProfit, TradeInfo &trades[])
{
    int size = ArraySize(trades);
    bool tradeFound = false;

    for(int i = 0; i < size; i++)
    {
        if(trades[i].positionID == positionID)
        {
            tradeFound = true;
            if(updateMaxProfit)
            {
                if(value > trades[i].maxProfit) // Only update if new value is greater
                {
                    trades[i].maxProfit = value;
                    PrintFormat("Updated MaxProfit: %.2f", trades[i].maxProfit);
                }
                else
                {
                    PrintFormat("MaxProfit not updated. Current: %.2f, New: %.2f", trades[i].maxProfit, value);
                }
            }
            else
            {
                if(value < trades[i].maxDrawdown) // Only update if new value is smaller (more negative)
                {
                    trades[i].maxDrawdown = value;
                    PrintFormat("Updated MaxDrawdown: %.2f", trades[i].maxDrawdown);
                }
                else
                {
                    PrintFormat("MaxDrawdown not updated. Current: %.2f, New: %.2f", trades[i].maxDrawdown, value);
                }
            }
            PrintFormat("Trade with PositionID %d updated. MaxProfit: %.2f, MaxDrawdown: %.2f",
                        trades[i].positionID, trades[i].maxProfit, trades[i].maxDrawdown);
            return;
        }
    }
    if(!tradeFound)
    {
        PrintFormat("Trade with PositionID %d not found.", positionID);
    }
}

void UpdateTradeProfit(ulong positionID, double profit, TradeInfo &trades[])
{
    int size = ArraySize(trades);
    bool tradeFound = false;

    for(int i = 0; i < size; i++)
    {
        if(trades[i].positionID == positionID)
        {
            tradeFound = true;
            trades[i].profit = profit; // Update profit
            PrintFormat("Updated Profit: %.2f", trades[i].profit);
            return;
        }
    }
    if(!tradeFound)
    {
        PrintFormat("Trade with PositionID %d not found.", positionID);
    }
}

void UpdateTradeDetailsByPosition(ulong positionID, ulong ticketNr,ulong type, double openPrice, double volume, string &symbol, datetime openTime, TradeInfo &trades[])
{
   int size = ArraySize(trades);
   for(int i = 0; i < size; i++)
   {
      if(trades[i].positionID == positionID)
      {
         trades[i].ticketNr = ticketNr; // Update ticket number
         trades[i].type = type;
         trades[i].openPrice = openPrice;
         trades[i].volume = volume;
         trades[i].symbol = symbol;
         trades[i].openTime = openTime;

         PrintFormat("Trade with PositionID %d updated with new details.", positionID);
         return;
      }
   }
   PrintFormat("Trade with PositionID %d not found.", positionID);
}

//-------------PRINTS-------------

void PrintAllTrades(const TradeInfo &trades[])
{
   int size = ArraySize(trades);
   for(int i = 0; i < size; i++)
   {
      PrintFormat("PositionID: %d, TicketNr: %d, Symbol: %s, Volume: %.2f, Open Price: %.5f, Max Profit: %.2f, Max Drawdown: %.2f, Profit: %.2f, Open Time: %s",
                  trades[i].positionID, trades[i].ticketNr, trades[i].symbol, trades[i].volume, trades[i].openPrice,
                  trades[i].maxProfit, trades[i].maxDrawdown, trades[i].profit, TimeToString(trades[i].openTime));
   }
}

#endif
