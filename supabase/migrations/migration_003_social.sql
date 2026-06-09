-- Create a table for Connected Social Accounts
create table if not exists public.social_accounts (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users on delete cascade not null,
  provider text not null, -- 'youtube', 'tiktok', 'instagram'
  account_name text not null,
  access_token text not null,
  refresh_token text,
  expires_at timestamp with time zone,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  unique (user_id, provider)
);

-- Enable Row Level Security for social_accounts
alter table public.social_accounts enable row level security;

create policy "Users can view their own social accounts." on public.social_accounts
  for select using (auth.uid() = user_id);

create policy "Users can insert their own social accounts." on public.social_accounts
  for insert with check (auth.uid() = user_id);

create policy "Users can update their own social accounts." on public.social_accounts
  for update using (auth.uid() = user_id);

create policy "Users can delete their own social accounts." on public.social_accounts
  for delete using (auth.uid() = user_id);

-- Create a table for Scheduled Posts
create table if not exists public.scheduled_posts (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users on delete cascade not null,
  clip_id uuid references public.clips on delete cascade not null,
  provider text not null, -- 'youtube', 'tiktok', 'instagram'
  title text not null,
  description text,
  scheduled_time timestamp with time zone not null,
  status text default 'scheduled' not null, -- 'scheduled', 'publishing', 'posted', 'failed'
  error_message text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security for scheduled_posts
alter table public.scheduled_posts enable row level security;

create policy "Users can view their own scheduled posts." on public.scheduled_posts
  for select using (auth.uid() = user_id);

create policy "Users can insert their own scheduled posts." on public.scheduled_posts
  for insert with check (auth.uid() = user_id);

create policy "Users can update their own scheduled posts." on public.scheduled_posts
  for update using (auth.uid() = user_id);

create policy "Users can delete their own scheduled posts." on public.scheduled_posts
  for delete using (auth.uid() = user_id);
