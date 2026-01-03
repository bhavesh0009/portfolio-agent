// Quick test script to verify database connection
const Database = require('better-sqlite3');
const path = require('path');

const DB_PATH = path.join(__dirname, '..', '.cache', 'portfolio.db');

console.log('Testing database connection...');
console.log('Database path:', DB_PATH);

try {
  const db = new Database(DB_PATH, { readonly: true });

  console.log('\n[SUCCESS] Database connection established!\n');

  // Test queries
  console.log('--- PORTFOLIOS ---');
  const portfolios = db.prepare('SELECT * FROM portfolios').all();
  console.log(`Found ${portfolios.length} portfolio(s):`);
  portfolios.forEach(p => {
    console.log(`  ID ${p.id}: ${p.profile} (${p.timestamp})`);
  });

  console.log('\n--- STOCKS ---');
  const stocks = db.prepare('SELECT COUNT(*) as count FROM stocks').get();
  console.log(`Total stocks: ${stocks.count}`);

  const sampleStocks = db.prepare('SELECT id, name, ticker, sector, allocation_pct FROM stocks LIMIT 3').all();
  console.log('Sample stocks:');
  sampleStocks.forEach(s => {
    console.log(`  ${s.name} (${s.ticker}) - ${s.sector} - ${s.allocation_pct}%`);
  });

  console.log('\n--- INVESTMENT VIEWS ---');
  const views = db.prepare('SELECT COUNT(*) as count FROM investment_views').get();
  console.log(`Total investment views: ${views.count}`);

  console.log('\n--- KEY METRICS ---');
  const metrics = db.prepare('SELECT COUNT(*) as count FROM key_metrics').get();
  console.log(`Total key metrics: ${metrics.count}`);

  db.close();
  console.log('\n[SUCCESS] All tests passed! Database is ready.');
  console.log('\nYou can now run: npm run dev');

} catch (error) {
  console.error('\n[ERROR] Database connection failed:');
  console.error(error.message);
  console.error('\nMake sure you have run the portfolio builder agent first:');
  console.error('  cd .. && python agents/portfolio_builder_agent_simple.py');
  process.exit(1);
}
