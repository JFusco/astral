export const assets = [
  {symbol:'BTC',name:'Bitcoin',icon:'₿',type:'crypto',price:67500,change:2.84,quantity:.18,basis:11340,color:'#bb9bea',radius:184,phase:2.6},
  {symbol:'ETH',name:'Ethereum',icon:'Ξ',type:'crypto',price:3400,change:1.92,quantity:2.2,basis:7040,color:'#a29ae1',radius:158,phase:.65},
  {symbol:'SPY',name:'S&P 500 ETF',icon:'S',type:'etf',price:580,change:.76,quantity:12,basis:6780,color:'#7bcbd5',radius:235,phase:3.65},
  {symbol:'QQQ',name:'Nasdaq 100 ETF',icon:'Q',type:'etf',price:490,change:1.24,quantity:10,basis:4780,color:'#77c4d6',radius:232,phase:5.65},
  {symbol:'SOL',name:'Solana',icon:'◎',type:'crypto',price:156,change:4.12,quantity:20,basis:2900,color:'#be9eea',radius:242,phase:1.60},
  {symbol:'GLD',name:'Gold ETF',icon:'G',type:'etf',price:244,change:.32,quantity:8,basis:1912,color:'#d6c291',radius:185,phase:4.55},
  {symbol:'TLT',name:'Treasury bond ETF',icon:'T',type:'etf',price:92.4,change:-.24,quantity:0,basis:0,color:'#779fba',radius:122,phase:3.10},
  {symbol:'IWM',name:'Russell 2000 ETF',icon:'I',type:'etf',price:217.8,change:1.08,quantity:0,basis:0,color:'#779fba',radius:266,phase:.04}
];
export function createPortfolio(){return {cash:72000,openingEquity:100000,realized:6752,fees:38.4,halted:false,assets:assets.map(a=>({...a})),sequence:0};}
export function totals(book){const deployed=book.assets.reduce((s,a)=>s+a.quantity*a.price,0);const basis=book.assets.reduce((s,a)=>s+a.basis,0);const equity=book.cash+deployed;return {deployed,equity,unrealized:deployed-basis,net:equity-book.openingEquity,exposure:equity?deployed/equity:0};}
export function fill(book,symbol,side,notional=500){
  const asset=book.assets.find(a=>a.symbol===symbol);if(!asset||!['buy','sell'].includes(side))return {ok:false,reason:'Invalid simulated order.'};
  if(!Number.isFinite(notional)||notional<=0||asset.price<=0)return {ok:false,reason:'Invalid order amount.'};
  if(side==='buy'&&book.halted)return {ok:false,reason:'New entries are halted. Demo sells remain available.'};
  let quantity=notional/asset.price;quantity=asset.type==='etf'?Math.floor(quantity):Math.floor(quantity*1e6)/1e6;
  if(side==='sell')quantity=Math.min(quantity,asset.quantity);
  if(quantity<=0)return {ok:false,reason:side==='sell'?'No simulated position to sell.':'Amount is below one ETF share.'};
  const value=quantity*asset.price;const fee=asset.type==='crypto'?value*.0025:0;const t=totals(book);
  if(side==='buy'){
    if(value+fee>book.cash)return {ok:false,reason:'Demo cash limit reached.'};
    if((t.deployed+value)/(t.equity-fee)>.5)return {ok:false,reason:'Demo portfolio limit: 50% deployed capital.'};
    if((asset.quantity*asset.price+value)/(t.equity-fee)>.2)return {ok:false,reason:'Demo asset limit: 20% of equity.'};
    book.cash-=value+fee;asset.quantity+=quantity;asset.basis+=value+fee;
  }else{
    const cost=asset.basis*(quantity/asset.quantity);book.cash+=value-fee;book.realized+=value-fee-cost;asset.quantity-=quantity;asset.basis-=cost;
    if(asset.quantity<1e-9){asset.quantity=0;asset.basis=0;}
  }
  book.fees+=fee;book.sequence++;
  return {ok:true,id:`SIM-${String(book.sequence).padStart(5,'0')}`,symbol,side,quantity,price:asset.price,value,fee,time:Date.now()};
}
