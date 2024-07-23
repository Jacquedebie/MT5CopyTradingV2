//+------------------------------------------------------------------+
//|                                                         RetrieveTrades.mq5 |
//|                        Copyright 2024, MetaQuotes Software Corp.           |
//|                                             https://www.mql5.com           |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

// Function to calculate drawdown, max profit, and actual profit in currency value
void CalculateDrawdownAndProfit(const ulong deal_ticket, double &max_drawdown_value, double &max_profit_value, double &actual_profit, ulong &ticket)
{
   double open_price = HistoryDealGetDouble(deal_ticket, DEAL_PRICE);
   string symbol = HistoryDealGetString(deal_ticket, DEAL_SYMBOL);
   datetime open_time = HistoryDealGetInteger(deal_ticket, DEAL_TIME);
   datetime close_time = HistoryDealGetInteger(deal_ticket, DEAL_TIME_MSC);
   double volume = HistoryDealGetDouble(deal_ticket, DEAL_VOLUME);
   int deal_type = HistoryDealGetInteger(deal_ticket, DEAL_ENTRY); // DEAL_ENTRY_IN for buy, DEAL_ENTRY_OUT for sell

   ticket = HistoryDealGetInteger(deal_ticket, DEAL_ORDER); // Get the trade ticket number
   actual_profit = HistoryDealGetDouble(deal_ticket, DEAL_PROFIT); // Get the actual profit of the trade

   double highest_price = open_price;
   double lowest_price = open_price;

   MqlRates rates[];
   int rates_total = CopyRates(symbol, PERIOD_M1, open_time, close_time, rates);
   if(rates_total > 0)
   {
      for(int i = 0; i < rates_total; i++)
      {
         if(deal_type == DEAL_ENTRY_IN) // Buy order
         {
            if(rates[i].low < lowest_price)
               lowest_price = rates[i].low;

            if(rates[i].high > highest_price)
               highest_price = rates[i].high;
         }
         else if(deal_type == DEAL_ENTRY_OUT) // Sell order
         {
            if(rates[i].high > highest_price)
               highest_price = rates[i].high;

            if(rates[i].low < lowest_price)
               lowest_price = rates[i].low;
         }
      }
   }
   else
   {
      Print("Error in retrieving rates: ", GetLastError());
   }

   // Calculate pip size and pip value
   double pip_size = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double pip_value = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE) * volume;

   // Calculate drawdown and max profit in monetary terms
   if (deal_type == DEAL_ENTRY_IN) // Buy order
   {
      max_drawdown_value = (open_price - lowest_price) / pip_size * pip_value;
      max_profit_value = (highest_price - open_price) / pip_size * pip_value;
   }
   else if (deal_type == DEAL_ENTRY_OUT) // Sell order
   {
      max_drawdown_value = (highest_price - open_price) / pip_size * pip_value;
      max_profit_value = (open_price - lowest_price) / pip_size * pip_value;
   }

   max_drawdown_value = -max_drawdown_value;
   max_drawdown_value = NormalizeDouble(max_drawdown_value, 2);
   max_profit_value = NormalizeDouble(max_profit_value, 2);
}

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   datetime current_time = TimeCurrent();
   datetime start_time = current_time - 3 * 30 * 24 * 60 * 60; // 3 months ago
   datetime end_time = current_time;
   HistorySelect(start_time, end_time);

   int total_orders = HistoryDealsTotal();

   // Save the file in the common folder
   string downloads_path = "trade_drawdown.txt";
   int file_handle = FileOpen(downloads_path, FILE_WRITE | FILE_CSV | FILE_COMMON, ",");
   if(file_handle == INVALID_HANDLE)
   {
      Print("Failed to open file");
      return(INIT_FAILED);
   }
   
   for(int i = 0; i < total_orders; i++)
   {
      ulong deal_ticket = HistoryDealGetTicket(i);
      double max_drawdown_value;
      double max_profit_value;
      double actual_profit;
      ulong ticket;
      CalculateDrawdownAndProfit(deal_ticket, max_drawdown_value, max_profit_value, actual_profit, ticket);
      
      Print("Trade Ticket: ", ticket, " Deal Ticket: ", deal_ticket, " Max Drawdown: ", max_drawdown_value, " Max Profit: ", max_profit_value, " Actual Profit: ", actual_profit, " Currency");
      
      // Debugging: Print deal details for verification
      string symbol = HistoryDealGetString(deal_ticket, DEAL_SYMBOL);
      double volume = HistoryDealGetDouble(deal_ticket, DEAL_VOLUME);
      datetime open_time = HistoryDealGetInteger(deal_ticket, DEAL_TIME);
      double open_price = HistoryDealGetDouble(deal_ticket, DEAL_PRICE);
      int deal_type = HistoryDealGetInteger(deal_ticket, DEAL_ENTRY); // DEAL_ENTRY_IN for buy, DEAL_ENTRY_OUT for sell
      Print("Trade Ticket: ", ticket, " Symbol: ", symbol, " Volume: ", volume, " Open Time: ", open_time, " Open Price: ", open_price, " Deal Type: ", deal_type);

      FileWrite(file_handle, deal_ticket, max_drawdown_value);
   }

   // Close the file after writing all trades
   FileClose(file_handle);
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Cleanup code if needed
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // No need to implement OnTick for this script
}
//+------------------------------------------------------------------+
