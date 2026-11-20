-- NutriRAG schema (run in Supabase SQL editor)

create table if not exists profiles (
  id text primary key,
  age integer not null check (age >= 1 and age <= 120),
  goal text not null,
  diet_type text not null,
  allergies text[] default '{}',
  daily_budget numeric not null check (daily_budget >= 0),
  updated_at timestamptz default now()
);

create table if not exists foods (
  id bigserial primary key,
  food_name text not null unique,
  serving_size text not null,
  calories numeric not null,
  protein numeric not null,
  carbohydrates numeric not null,
  fat numeric not null,
  estimated_cost numeric not null default 0,
  source text,
  diet_tags text[] default '{}',
  allergens text[] default '{}'
);

create table if not exists nutrition_notes (
  id bigserial primary key,
  topic text not null,
  content text not null,
  source text
);

-- Optional: allow anon key read/write for academic demo
alter table profiles enable row level security;
alter table foods enable row level security;
alter table nutrition_notes enable row level security;

drop policy if exists "public read foods" on foods;
create policy "public read foods" on foods for select using (true);
drop policy if exists "public write foods" on foods;
create policy "public write foods" on foods for all using (true) with check (true);

drop policy if exists "public read notes" on nutrition_notes;
create policy "public read notes" on nutrition_notes for select using (true);
drop policy if exists "public write notes" on nutrition_notes;
create policy "public write notes" on nutrition_notes for all using (true) with check (true);

drop policy if exists "public read profiles" on profiles;
create policy "public read profiles" on profiles for select using (true);
drop policy if exists "public write profiles" on profiles;
create policy "public write profiles" on profiles for all using (true) with check (true);
